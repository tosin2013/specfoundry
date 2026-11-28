package author

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/tosin2013/chalkeus/internal/evidence"
)

// File is one drafted file: its path in the item folder and its SHA-256, never its contents.
type File struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
}

// JobRecord is one author Job of an automatic draft (024 FR-006): names, spend and results only.
type JobRecord struct {
	Attempt     int            `json:"attempt"`
	Namespace   string         `json:"namespace"`
	Outcome     string         `json:"outcome"` // the Job's end: Complete | Failed | DeadlineExceeded | Timeout | cancelled
	HarnessExit any            `json:"harness_exit"`
	Spend       map[string]any `json:"spend,omitempty"`
	Error       string         `json:"error,omitempty"`
	DraftFiles  int            `json:"draft_files"`
	Checks      []AuthorCheck  `json:"checks,omitempty"`
	Model       string         `json:"model,omitempty"` // 041: the model the author Job used
}

// AuthorCheck is one isolation check of the author's namespace (A01-A05, 024 R6).
type AuthorCheck struct {
	ID     string `json:"id"`
	Result string `json:"result"` // pass | fail
	Detail string `json:"detail"`
}

// CheckRecord is one `author check`.
type CheckRecord struct {
	At        string `json:"at"`
	DraftHash string `json:"draft_hash"`
	Result    string `json:"result"` // DRAFT_OK or a code
	GradePath string `json:"grade_json,omitempty"`
}

// Draft is a draft's evidence (data-model.md). It holds names, hashes and results only.
type Draft struct {
	ID             string         `json:"draft_id"`
	Target         string         `json:"target"`
	Repo           string         `json:"repo"`
	Item           string         `json:"item"`
	Slice          string         `json:"slice,omitempty"` // 026: the slice the draft is for
	Title          string         `json:"title,omitempty"`
	SpecSHA256     string         `json:"spec_sha256"`
	BaseRevision   string         `json:"base_revision"`
	Level          string         `json:"level"`
	Identity       string         `json:"identity"`
	CanWriteTarget bool           `json:"can_write_target"`
	Companion      string         `json:"companion"`
	CompanionDir   string         `json:"companion_dir"`
	Workspace      string         `json:"workspace"`
	Files          []File         `json:"files"`
	Checks         []CheckRecord  `json:"checks"`
	Mapping        map[string]any `json:"mapping,omitempty"`
	PR             map[string]any `json:"pr,omitempty"`
	State          string         `json:"state"` // started | checked(pass) | checked(fail) | submitted
	Readiness      map[string]any `json:"readiness,omitempty"`
	// 024: how the draft started, the author Jobs of an automatic draft, and the watcher's decision.
	Trigger       string      `json:"trigger,omitempty"` // manual | auto
	Jobs          []JobRecord `json:"jobs,omitempty"`
	WatchDecision string      `json:"watch_decision,omitempty"`
	// 041: the model that wrote the draft (the last author Job's); "" for a draft written by hand.
	Model string `json:"model,omitempty"`

	// lastOutput is the drafted tests' output from the last check (never stored; 018 FR, 024 R5).
	lastOutput string

	dir string
}

// Root is where draft evidence lives: <evidence root>/drafts.
func Root(evidenceRoot string) string { return filepath.Join(evidenceRoot, "drafts") }

// DraftRoots are every draft folder of the checkout that holds evidenceRoot, the current one
// first: each Spec Kit feature's `specs/<feature>/evidence/drafts` and `pilot/runs/drafts`.
// An evidence root outside that layout has only its own.
func DraftRoots(evidenceRoot string) []string {
	cur := Root(evidenceRoot)
	repo := ""
	abs, err := filepath.Abs(evidenceRoot)
	if err == nil {
		switch {
		case filepath.Base(abs) == "evidence" && filepath.Base(filepath.Dir(filepath.Dir(abs))) == "specs":
			repo = filepath.Dir(filepath.Dir(filepath.Dir(abs))) // <repo>/specs/<feature>/evidence
		case filepath.Base(abs) == "runs" && filepath.Base(filepath.Dir(abs)) == "pilot":
			repo = filepath.Dir(filepath.Dir(abs)) // <repo>/pilot/runs
		}
	}
	out := []string{cur}
	if repo == "" {
		return out
	}
	seen := map[string]bool{filepath.Clean(cur): true}
	if a, err := filepath.Abs(cur); err == nil {
		seen[a] = true
	}
	more, _ := filepath.Glob(filepath.Join(repo, "specs", "*", "evidence", "drafts"))
	sort.Strings(more)
	for _, d := range append(more, filepath.Join(repo, "pilot", "runs", "drafts")) {
		if !seen[d] {
			seen[d] = true
			out = append(out, d)
		}
	}
	return out
}

// NewDraft creates a draft folder named by the UTC time.
func NewDraft(root string) (*Draft, error) {
	if err := os.MkdirAll(root, 0o755); err != nil {
		return nil, err
	}
	for i := 0; i < 5; i++ {
		id := time.Now().UTC().Format("20060102T150405Z")
		dir := filepath.Join(root, id)
		if err := os.Mkdir(dir, 0o755); err == nil {
			return &Draft{ID: id, State: "started", dir: dir, Files: []File{}, Checks: []CheckRecord{}}, nil
		}
		time.Sleep(time.Second)
	}
	return nil, fmt.Errorf("could not create a draft folder in %s", root)
}

// LoadDraft reads a draft by id, or the latest draft of target/item when id is "".
func LoadDraft(root, id, target, item string) (*Draft, error) {
	if id == "" {
		entries, _ := os.ReadDir(root)
		var ids []string
		for _, e := range entries {
			if e.IsDir() {
				ids = append(ids, e.Name())
			}
		}
		sort.Sort(sort.Reverse(sort.StringSlice(ids)))
		for _, x := range ids {
			d, err := LoadDraft(root, x, "", "")
			if err == nil && d.Target == target && d.Item == item {
				return d, nil
			}
		}
		return nil, fmt.Errorf("no draft for target %s item %s: run `./chalkeus forge author start` first", target, item)
	}
	raw, err := os.ReadFile(filepath.Join(root, id, "draft.json"))
	if err != nil {
		return nil, err
	}
	var d Draft
	if err := json.Unmarshal(raw, &d); err != nil {
		return nil, err
	}
	d.dir = filepath.Join(root, id)
	return &d, nil
}

// Dir is the draft's evidence folder.
func (d *Draft) Dir() string { return d.dir }

// Save writes draft.json.
func (d *Draft) Save() error { return evidence.WriteJSON(filepath.Join(d.dir, "draft.json"), d) }

// Event appends one line to events.jsonl (names, codes and counts only).
func (d *Draft) Event(event, detail string) error {
	f, err := os.OpenFile(filepath.Join(d.dir, "events.jsonl"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer func() { _ = f.Close() }()
	raw, _ := json.Marshal(map[string]any{"at": evidence.Now(), "event": event, "detail": detail})
	_, err = f.Write(append(raw, '\n'))
	return err
}
