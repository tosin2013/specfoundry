package cli

import (
	"context"
	"errors"
	"fmt"
	"github.com/tosin2013/chalkeus/internal/grader"
	"github.com/tosin2013/chalkeus/internal/scm/hosts"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/cobra"

	"github.com/tosin2013/chalkeus/internal/author"
	"github.com/tosin2013/chalkeus/internal/cluster"
	"github.com/tosin2013/chalkeus/internal/cnitoken"
	"github.com/tosin2013/chalkeus/internal/config"
	"github.com/tosin2013/chalkeus/internal/doctor"
	"github.com/tosin2013/chalkeus/internal/fixture"
	"github.com/tosin2013/chalkeus/internal/gate"
	"github.com/tosin2013/chalkeus/internal/images"
	"github.com/tosin2013/chalkeus/internal/paths"
	"github.com/tosin2013/chalkeus/internal/readiness"
)

// doctorCmd is `./chalkeus forge doctor --target <name> [--item NNN] [--baseline]` (014): a read-only
// preflight that lists every problem in one pass. It never prints hidden-test contents.
func doctorCmd() *cobra.Command {
	c := &cobra.Command{
		Use:   "doctor --target <name> [--item NNN [--slice <id>]] [--baseline]",
		Short: "read-only preflight: check a target's profile, cluster and GitHub access, and one item's readiness, reporting every problem at once",
		Args:  cobra.NoArgs,
		RunE:  runDoctor,
	}
	addTargetFlag(c)
	requireTarget(c)
	c.Flags().String("item", "", "also check roadmap item NNN: every readiness rule, without stopping at the first problem")
	c.Flags().Bool("baseline", false, "with --item: on the cluster, check that the install and test commands pass on today's code, offline")
	c.Flags().String("slice", "", "with --item: check this slice of the item (026), and with --baseline run the slice baseline")
	return c
}

func runDoctor(cmd *cobra.Command, _ []string) error {
	out := cmd.OutOrStdout()
	item, _ := cmd.Flags().GetString("item")
	withBaseline, _ := cmd.Flags().GetBool("baseline")
	sliceID, _ := cmd.Flags().GetString("slice")
	if withBaseline && item == "" {
		return Exit(ExitError, "--baseline needs --item NNN")
	}
	if sliceID != "" && item == "" {
		return Exit(ExitError, "--slice needs --item NNN")
	}
	var r doctor.Report
	defer func() { r.Print(out) }()
	l, err := layout()
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	// Host (031): the machine, its container runtime, then (after `up`) the node and image
	// platforms. Reported first, so a stopped Docker Desktop shows even when the profile fails.
	r.HostRows(doctor.ProbeHost(), doctor.ProbeRuntime())
	if pins, err := paths.ReadEnv(l.Pins); err == nil && pins["SPEC_VERSION"] != "" {
		st, det := doctor.SpecRow(specVersion(), pins["SPEC_VERSION"])
		r.Add("host", "spec-status", st, det)
	}

	// Profile.
	cfg, err := config.Load(l.Root, false, false)
	if !r.OK("profile", "forge.env", err, "") {
		return Code(ExitFail)
	}
	t, err := loadTarget(cmd, l, cfg)
	if !r.OK("profile", "target profile", err, fmt.Sprintf("%s (%s@%s), toolchain %s, level %s", t.Name, t.Repo, t.Branch, t.Toolchain, t.SecurityLevel)) {
		return Code(ExitFail)
	}
	if t.Fixture {
		return Exit(ExitError, "doctor checks a --target repository, not the fixture")
	}
	if t.SecurityLevel == config.LevelRecommended {
		_, err := t.AuthorToken()
		r.OK("profile", "test author token (recommended level)", err, "present, mode 0600")
	}
	if t.AuthorAuto == "on" { // 024: who drafts hidden tests, as information only
		r.Add("profile", "auto-draft", doctor.Info, fmt.Sprintf("on: `./chalkeus forge author watch --target %s` drafts ready items (every %d s, up to %d author Job(s) each)", t.Name, t.AuthorIntervalS, t.AuthorAttempts))
	} else {
		r.Add("profile", "auto-draft", doctor.Info, "off: hidden tests are drafted by hand (set FORGE_AUTHOR_AUTO=on to let `author watch` draft them)")
	}

	// Machine and cluster.
	if hosts := cfg.ModelHosts(); len(hosts) == 0 {
		r.Add("cluster", "model host", doctor.Fail, "FORGE_MODEL_EGRESS_HOSTS is empty in forge.env")
	} else {
		r.Add("cluster", "model host", doctor.Pass, fmt.Sprintf("%d host(s) configured", len(hosts)))
	}
	// The model key: one tiny request from this machine with the worker's model (a blocked key
	// used to show up only after every attempt had failed).
	if probe, err := cfg.ProbeModel(ctx); err != nil {
		r.Add("cluster", "model key", doctor.Fail, err.Error())
	} else {
		switch {
		case probe.Status >= 200 && probe.Status < 300:
			r.Add("cluster", "model key", doctor.Pass, "the provider accepts the worker's key (provider "+probe.Provider+")")
		case probe.Status == 401 || probe.Status == 403:
			r.Add("cluster", "model key", doctor.Fail, fmt.Sprintf("the provider rejected the worker's key (%d): %s. Fix or replace the key, then run `./chalkeus forge import-opencode` again",
				probe.Status, probe.Message))
		default:
			r.Add("cluster", "model key", doctor.Warn, fmt.Sprintf("couldn't confirm the key: the provider answered %d to a one-token test request", probe.Status))
		}
	}
	doctorAuthorModel(ctx, &r, cfg, t)
	if msg := cluster.OldMessage(cluster.OldPresent()); msg != "" {
		r.Add("cluster", "old cluster", doctor.Warn, msg+" (027)")
	}
	upOK := false
	_, kindErr := exec.LookPath("kind")
	if _, err := os.Stat(l.UpOK); err != nil {
		r.Add("cluster", "pilot up", doctor.Fail, "`./chalkeus forge up` has not completed")
	} else if kindErr == nil && !cluster.Exists() {
		r.Add("cluster", "pilot up", doctor.Fail, "no kind cluster "+paths.Cluster+" (renamed in 027, or deleted); run `./chalkeus forge up`")
	} else {
		upOK = true
		r.Add("cluster", "pilot up", doctor.Pass, "")
		running, err1 := images.Load(l)
		lock, err2 := images.ReadLock(l)
		if err := errors.Join(err1, err2); err != nil {
			r.Add("cluster", "images", doctor.Fail, err.Error())
		} else {
			src, _ := os.ReadFile(l.ImageSource)
			st, det := doctor.ImagesRow(strings.TrimSpace(string(src)), running, lock)
			r.Add("cluster", "images", st, det)
			// 031 T034: Calico's CNI token (a Mac's sleeping VM can let it expire unrenewed).
			if exp, err := cnitoken.NodeExpiry(paths.Cluster + "-control-plane"); err != nil {
				st, det := doctor.NetworkTokenRow(0, err)
				r.Add("cluster", "network token", st, det)
			} else {
				st, det := doctor.NetworkTokenRow(time.Until(exp), nil)
				r.Add("cluster", "network token", st, det)
			}
			// 031: the node's platform, and a build of every pinned image for it.
			if node, err := doctor.ProbeNodePlatform(paths.Context); err != nil {
				r.Add("cluster", "node platform", doctor.Warn, "couldn't read the node's platform: "+err.Error())
			} else {
				st, det := doctor.NodePlatformRow(node)
				r.Add("cluster", "node platform", st, det)
				if st == doctor.Pass {
					source := strings.TrimSpace(string(src))
					var infos map[string]doctor.ImageInfo
					if source != "local-build" {
						infos = doctor.ProbeImages(doctor.LockImages(lock))
					}
					st, det := doctor.ImagePlatformsRow(source, node, infos)
					r.Add("cluster", "image platforms", st, det)
				}
			}
		}
	}

	// Git host access (037: through the host interface; GitHub's rows read as before).
	h := t.Host()
	area, tokenRow := "github", "your GitHub token"
	if !h.IsGitHub() {
		area, tokenRow = "scm", "your "+h.Name+" token"
	}
	sc, err := hosts.Operator(h)
	if !r.OK(area, tokenRow, err, "") {
		return Code(ExitFail)
	}
	for _, repo := range []string{t.Repo, t.CompanionRepo} {
		_, err := sc.Repository(ctx, repo)
		r.OK(area, "can read "+repo, err, "")
	}
	id, err := author.ResolveIdentity(ctx, t)
	switch {
	case err != nil:
		r.Add("github", "test author identity", doctor.Warn, err.Error()+" (needed only to draft hidden tests with the test author)")
	case id.CanWriteTarget:
		r.Add("github", "test author identity", doctor.Pass, fmt.Sprintf("%s (level %s; it can also write the target)", id.Login, id.Level))
	default:
		r.Add("github", "test author identity", doctor.Pass, fmt.Sprintf("%s (level %s; companion only)", id.Login, id.Level))
	}
	switch prot, err := sc.BranchProtection(ctx, t.Repo, t.Branch); {
	case err != nil:
		r.Add(area, "branch protection", doctor.Warn, "could not check: "+err.Error())
	case !prot.Protected:
		r.Add(area, "branch protection", doctor.Warn, t.Repo+"@"+t.Branch+" is not protected; protect it so changes arrive only by reviewed PR (important at the minimal level)")
	default:
		r.Add(area, "branch protection", doctor.Pass, t.Branch+" is protected")
	}
	doctorRoadmap(&r, t)
	doctorCI(ctx, &r, l, t) // 036: the target's CI, compared with the profile (warnings only)
	if item == "" {
		return doctorExit(&r)
	}

	// The item: every readiness rule.
	deps := readiness.Deps{Src: gate.ExecStatus{}, AllRules: true, Slice: sliceID,
		Clone: func(repo, branch string) (string, string, error) {
			return fixture.FreshClone(t.Host(), repo, branch, 1)
		},
		OpenPRHeads: func(repo string) ([]string, error) {
			return hosts.OpenPilotHeads(ctx, sc, repo)
		}}
	res, err := readiness.Check(deps, t, item, 0, "")
	if !r.OK("item", "readiness", err, "") {
		return Code(ExitFail)
	}
	r.Readiness(res)
	if res.SpecDir != "" && res.Commit != "" { // 033: research tasks and runtime versions (warnings)
		var phases []string
		if res.Slice != nil {
			phases = res.Slice.Phases
		}
		doctorTasks(ctx, &r, sc, l, t, res.SpecDir, res.Commit, phases)
	}
	if !withBaseline {
		return doctorExit(&r)
	}

	// The project on the cluster, offline: toolchain, install, the project's tests on today's code.
	if !upOK {
		r.Add("baseline", "project tests offline", doctor.Skip, "needs `./chalkeus forge up`")
		return doctorExit(&r)
	}
	if res.Commit == "" || res.SpecDir == "" {
		r.Add("baseline", "project tests offline", doctor.Skip, "needs the item's spec and a readable target")
		return doctorExit(&r)
	}
	p, err := pipelineFor(cmd)
	if !r.OK("baseline", "pipeline", err, "") {
		return doctorExit(&r)
	}
	overlay, hasHidden, err := doctorOverlay(t, item, res)
	if !r.OK("baseline", "hidden tests overlay", err, "") {
		return doctorExit(&r)
	}
	_, _ = fmt.Fprintln(out, "doctor: running the item's baseline on the cluster (a few minutes)...")
	dir := filepath.Join(l.Build, "doctor", time.Now().UTC().Format("20060102T150405Z"))
	defer func() { _ = os.RemoveAll(dir) }()
	report, _, err := p.ItemBaseline(dir, "doctor-"+filepath.Base(dir), item, res, overlay, false)
	if !r.OK("baseline", "toolchain, install and prefetch", err, "") {
		return doctorExit(&r)
	}
	by := map[string]string{}
	checks, _ := report["checks"].([]any)
	for _, x := range checks {
		c, _ := x.(map[string]any)
		by[fmt.Sprint(c["id"])] = fmt.Sprint(c["result"])
	}
	if by["G4_visible_tests"] == "pass" {
		r.Add("baseline", "project tests offline", doctor.Pass, "the test command passes on today's code with no network")
		doctorAllowance(&r, toInt(report["test_seconds"]), doctorDeadline(l, t)) // 033 FR-013
	} else {
		r.Add("baseline", "project tests offline", doctor.Fail, "the test command fails on today's code with no network (see BASELINE_SUITE_FAILS in docs/troubleshooting.md)")
	}
	if res.Slice != nil && len(res.Slice.Earlier) > 0 { // 026: earlier slices' hidden tests on today's code
		switch by["G8_earlier_slices_kept"] {
		case "pass":
			r.Add("baseline", "earlier slices' hidden tests pass on today's code", doctor.Pass, strings.Join(res.Slice.Earlier, ", "))
		case "fail":
			r.Add("baseline", "earlier slices' hidden tests pass on today's code", doctor.Fail, "a merged slice's hidden tests fail (EARLIER_SLICE_BROKEN_ON_BASE)")
		default:
			r.Add("baseline", "earlier slices' hidden tests pass on today's code", doctor.Skip, "not checked: the project's own tests fail first")
		}
	}
	switch {
	case !hasHidden:
		r.Add("baseline", "hidden tests fail on today's code", doctor.Skip, "no hidden tests yet")
	case by["G5_hidden_tests"] == "pass":
		r.Add("baseline", "hidden tests fail on today's code", doctor.Pass, "")
	case by["G5_hidden_tests"] == "fail": // in a baseline, G5 fails when the hidden tests pass
		r.Add("baseline", "hidden tests fail on today's code", doctor.Fail, "the hidden tests already pass (BASELINE_HIDDEN_PASSES)")
	default: // not graded: the project's own tests failed first (found by the 025 gaps scenario)
		r.Add("baseline", "hidden tests fail on today's code", doctor.Skip, "not checked: the project's own tests fail first; fix them, then run doctor again")
	}
	return doctorExit(&r)
}

// doctorOverlay is the item's hidden tests, or, when there are none yet, a placeholder file that
// isn't a test, so the baseline still proves the project's own tests run offline.
func doctorOverlay(t config.Target, item string, res readiness.Result) ([]byte, bool, error) {
	if res.HiddenFiles > 0 {
		cdir, commit, err := fixture.FreshClone(t.Host(), t.CompanionRepo, "", 1)
		if err != nil {
			return nil, false, err
		}
		defer func() { _ = os.RemoveAll(cdir) }()
		dirs := res.Overlay // 026: the slice's folder, or every slice folder for a sliced item
		if len(dirs) == 0 {
			dirs = []string{t.CompanionItemDir(item)}
		}
		tarb, _, err := grader.OverlayDirs(cdir, t.CompanionRepo, commit, dirs, item)
		return tarb, true, err
	}
	d, err := os.MkdirTemp("", "pilot-doctor-")
	if err != nil {
		return nil, false, err
	}
	defer func() { _ = os.RemoveAll(d) }()
	if err := os.WriteFile(filepath.Join(d, ".chalkeus-doctor"), []byte("placeholder, not a test\n"), 0o644); err != nil {
		return nil, false, err
	}
	tarb, _, err := grader.Overlay(d, t.CompanionRepo, "none", ".", item)
	return tarb, false, err
}

func doctorExit(r *doctor.Report) error {
	if r.Failed() {
		return Code(ExitFail)
	}
	return nil
}

// doctorRoadmap adds the target's roadmap: every active item and what the pilot needs next.
func doctorRoadmap(r *doctor.Report, t config.Target) {
	dir, _, err := fixture.FreshClone(t.Host(), t.Repo, t.Branch, 1)
	if err != nil {
		r.Add("roadmap", "clone", doctor.Warn, "could not clone "+t.Repo+": "+err.Error())
		return
	}
	defer func() { _ = os.RemoveAll(dir) }()
	_, stdout := gate.ExecStatus{}.Status(dir)
	cdir, _, cerr := fixture.FreshClone(t.Host(), t.CompanionRepo, "", 1)
	if cerr == nil {
		defer func() { _ = os.RemoveAll(cdir) }()
	}
	r.Roadmap(stdout, dir, func(item string) string {
		if cerr != nil {
			return ""
		}
		return filepath.Join(cdir, filepath.FromSlash(t.CompanionItemDir(item)))
	})
}

// specVersion is the first line of the host's `spec --version`, or "" when it can't run.
func specVersion() string {
	bin := os.Getenv("SPEC_BIN")
	if bin == "" {
		bin = "spec"
	}
	out, err := exec.Command(bin, "--version").Output()
	if err != nil {
		return ""
	}
	return strings.SplitN(strings.TrimSpace(string(out)), "\n", 2)[0]
}
