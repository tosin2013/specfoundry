package author

import (
	"archive/tar"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"strings"
	"time"

	"github.com/tosin2013/chalkeus/internal/frame"
	"github.com/tosin2013/chalkeus/internal/k8s"
	"github.com/tosin2013/chalkeus/internal/runner"
	"github.com/tosin2013/chalkeus/internal/stage"
	"github.com/tosin2013/chalkeus/internal/verbose"
)

// JobCluster is what an author Job needs from the cluster (a *k8s.Client in production).
type JobCluster interface {
	Apply(yamlText string) error
	CreateSecretFromFiles(ns, name string, files []string) error
	StageInputs(ns, job, container, stageDir string, tarball []byte, timeout time.Duration) error
	DeleteNS(ns string, wait bool)
}

// JobEnv runs author Jobs (024 R3).
type JobEnv struct {
	Manifests  string // pilot/manifests
	Cluster    JobCluster
	Runner     runner.Runner
	Images     map[string]string // worker, tools
	Model      string            // PILOT_MODEL
	SpendCap   string
	TokenCap   string
	ModelFiles []string // the worker's opencode.json and key file (the only Secret)
	Deadline   int      // seconds
	FreeModels bool     // the target opted in to OpenCode's free models
	// Checks runs A01-A05 against the running author namespace (nil skips them, in tests).
	Checks func(ns, draftID string) []AuthorCheck
}

// AuthorNS is an automatic draft's namespace.
func AuthorNS(target, item string) string { return "pilot-a-" + target + "-" + item }

// RunJob runs one author Job for a draft: it stages the workspace (spec, plan, tasks, criteria,
// base/ and the current draft/) and the prompt, runs the Job, and replaces the workspace's
// draft/ with the Job's draft.tar. The namespace is deleted afterwards. The draft leaves the Job
// only through its framed output (024 FR-005).
func RunJob(ctx context.Context, je JobEnv, d *Draft, attempt int, prompt string) JobRecord {
	ns := AuthorNS(d.Target, d.Item)
	rec := JobRecord{Attempt: attempt, Namespace: ns, Model: je.Model}
	d.Model = je.Model // 041: recorded per draft and named in the PR body
	fail := func(reason string, err error) JobRecord {
		rec.Error = reason
		if err != nil {
			rec.Error = reason + ": " + clip(err.Error())
		}
		return rec
	}
	if je.Images["worker"] == "" || je.Images["tools"] == "" {
		return fail("harness_error", fmt.Errorf("no worker or tools image: run `./chalkeus forge up`"))
	}
	je.Cluster.DeleteNS(ns, true)
	defer je.Cluster.DeleteNS(ns, false)
	nsYAML, err := k8s.Render(filepath.Join(je.Manifests, "author-ns.yaml.tmpl"), map[string]string{"NS": ns, "DRAFT_ID": d.ID})
	if err != nil {
		return fail("harness_error", err)
	}
	jobYAML, err := k8s.Render(filepath.Join(je.Manifests, "author-job.yaml.tmpl"), map[string]string{"NS": ns,
		"DEADLINE": fmt.Sprint(je.Deadline), "TOOLS_IMAGE": je.Images["tools"], "WORKER_IMAGE": je.Images["worker"],
		"PILOT_MODEL": je.Model, "SPEND_CAP": je.SpendCap, "TOKEN_CAP": je.TokenCap, "INPUT_LIMIT": "1Gi",
		"DISABLE_FREE_MODELS": disableFree(je.FreeModels)})
	if err != nil {
		return fail("harness_error", err)
	}
	ws, err := workspaceTar(d.Workspace)
	if err != nil {
		return fail("harness_error", err)
	}
	meta, _ := json.Marshal(map[string]any{"role": "author", "draft_id": d.ID, "item": d.Item, "attempt": attempt})
	in := stage.New()
	for name, b := range map[string][]byte{"meta.json": meta, "prompt.md": []byte(prompt), "workspace.tar": ws} {
		if err := in.AddBytes(name, b); err != nil {
			return fail("harness_error", err)
		}
	}
	inTar, err := in.Bytes()
	if err != nil {
		return fail("harness_error", err)
	}
	if err := je.Cluster.Apply(nsYAML); err != nil {
		return fail("harness_error", err)
	}
	if err := je.Cluster.CreateSecretFromFiles(ns, "model-key", je.ModelFiles); err != nil {
		return fail("harness_error", err)
	}
	h, err := je.Runner.Submit("author", ns, "author", jobYAML, true)
	if err != nil {
		return fail("harness_error", err)
	}
	defer je.Runner.Delete(h)
	if err := je.Cluster.StageInputs(ns, "author", "receiver", "/stage", inTar, 5*time.Minute); err != nil {
		return fail("harness_error", err)
	}
	verbose.V(1, "author %s: inputs staged (%d bytes), prompt %d bytes", ns, len(inTar), len(prompt))
	if je.Checks != nil {
		rec.Checks = je.Checks(ns, d.ID)
		for _, c := range rec.Checks {
			verbose.V(1, "author %s: %s %s %s", ns, strings.ToUpper(c.Result), c.ID, c.Detail)
		}
	}
	done := make(chan string, 1)
	go func() { done <- je.Runner.Wait(h, time.Duration(je.Deadline+90)*time.Second) }()
	select {
	case <-ctx.Done():
		rec.Outcome = "cancelled"
		return fail("cancelled", nil)
	case rec.Outcome = <-done:
	}
	files, ferr := frame.Decode(je.Runner.Collect(h), "report.json")
	if files == nil {
		return fail("no_result", fmt.Errorf("%s", ferr))
	}
	var report struct {
		Harness struct {
			Exit any `json:"exit"`
		} `json:"harness"`
		Spend map[string]any `json:"spend"`
		Error *string        `json:"error"`
	}
	_ = json.Unmarshal(files["report.json"], &report)
	rec.HarnessExit, rec.Spend = report.Harness.Exit, report.Spend
	if report.Error != nil {
		rec.Error = *report.Error
	}
	verbose.V(1, "author %s: harness exit %v, spend %v, error %q", ns, rec.HarnessExit, rec.Spend, rec.Error)
	if b, ok := files["draft.tar"]; ok {
		n, err := unpackDraft(b, filepath.Join(d.Workspace, "draft"))
		if err != nil {
			return fail("bad_draft", err)
		}
		rec.DraftFiles = n
	}
	return rec
}

// workspaceTar packs the draft workspace: regular files and directories only, no links.
func workspaceTar(ws string) ([]byte, error) {
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	err := filepath.WalkDir(ws, func(p string, e fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(ws, p)
		if rel == "." || (!e.IsDir() && !e.Type().IsRegular()) {
			return nil
		}
		info, err := e.Info()
		if err != nil {
			return err
		}
		hdr := &tar.Header{Name: filepath.ToSlash(rel), Mode: 0o644, ModTime: time.Unix(0, 0)}
		if e.IsDir() {
			hdr.Typeflag, hdr.Name, hdr.Mode = tar.TypeDir, hdr.Name+"/", 0o755
			return tw.WriteHeader(hdr)
		}
		hdr.Typeflag, hdr.Size = tar.TypeReg, info.Size()
		if err := tw.WriteHeader(hdr); err != nil {
			return err
		}
		f, err := os.Open(p)
		if err != nil {
			return err
		}
		defer func() { _ = f.Close() }()
		_, err = io.Copy(tw, f)
		return err
	})
	if err != nil {
		return nil, err
	}
	if err := tw.Close(); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// unpackDraft replaces dst (the workspace's draft/) with the regular files under draft/ in the
// Job's draft.tar. A link, an absolute path or a path leaving draft/ refuses the whole tar.
func unpackDraft(b []byte, dst string) (int, error) {
	type file struct {
		rel  string
		data []byte
	}
	var files []file
	tr := tar.NewReader(bytes.NewReader(b))
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return 0, err
		}
		name := path.Clean(hdr.Name)
		if hdr.Typeflag == tar.TypeDir {
			if name != "draft" && !strings.HasPrefix(name, "draft/") {
				return 0, fmt.Errorf("unexpected folder %q", hdr.Name)
			}
			continue
		}
		if hdr.Typeflag != tar.TypeReg {
			return 0, fmt.Errorf("%q is not a regular file", hdr.Name)
		}
		if path.IsAbs(name) || !strings.HasPrefix(name, "draft/") || strings.Contains(name, "..") {
			return 0, fmt.Errorf("%q is outside draft/", hdr.Name)
		}
		data, err := io.ReadAll(io.LimitReader(tr, 4<<20))
		if err != nil {
			return 0, err
		}
		files = append(files, file{strings.TrimPrefix(name, "draft/"), data})
	}
	if err := os.RemoveAll(dst); err != nil {
		return 0, err
	}
	if err := os.MkdirAll(dst, 0o755); err != nil {
		return 0, err
	}
	for _, f := range files {
		p := filepath.Join(dst, filepath.FromSlash(f.rel))
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			return 0, err
		}
		if err := os.WriteFile(p, f.data, 0o644); err != nil {
			return 0, err
		}
	}
	return len(files), nil
}

// disableFree mirrors worker.DisableFreeModels (no import: author doesn't depend on worker).
func disableFree(allow bool) string {
	if allow {
		return "0"
	}
	return "1"
}
