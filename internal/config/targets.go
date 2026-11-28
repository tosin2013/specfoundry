package config

import (
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/tosin2013/chalkeus/internal/scm"
)

// Target profiles (014, specs/014-any-project/contracts/target-profile.md): one file per target
// repository beside pilot.env. The target repository itself declares nothing (owner decision
// 2026-11-17); cluster mode (011) holds the same fields in a cluster resource.

// FixtureTarget is the implicit target built from pilot.env alone.
const FixtureTarget = "fixture"

var (
	targetNameRE = regexp.MustCompile(`^[a-z0-9][a-z0-9-]{0,30}$`)
	hostRE       = regexp.MustCompile(`^[A-Za-z0-9.-]+$`)
	quantityRE   = regexp.MustCompile(`^[0-9]+(Mi|Gi)$`)
	cpuRE        = regexp.MustCompile(`^([0-9]+|[0-9]+m|[0-9]+\.[0-9]+)$`) // Kubernetes CPU: 2, 3500m, 1.5
	digestRefRE  = regexp.MustCompile(`^[a-z0-9./:_-]+@sha256:[0-9a-f]{64}$`)
)

// Target is one configured target repository.
type Target struct {
	Name            string
	Repo            string
	Branch          string
	Toolchain       string
	ToolchainImage  string // operator-supplied toolchain image (digest-pinned), "" for the catalog's
	TestCommand     string
	InstallCommand  string   // installs the project\'s dependencies (prefetch and worker; 014 R7)
	ChangeType      string   // Conventional Commits type of the item's PR title (default feat)
	TestPaths       []string // the project's test files (globs): attempts must add tests and keep existing ones (G6, G7)
	RegistryHosts   []string
	CompanionRepo   string
	CompanionPath   string // folder inside the companion that holds items/ ("" = the root); one repo can serve many targets
	GithubIssues    string // on|off
	GithubApprovals string // on|off
	GraderMemory    string // optional override, e.g. 3Gi
	GraderDeadlineS int    // optional override, 0 = catalog default
	// 030: the worker's budget, raise-only (images.CheckTarget checks the floors); "" or 0 = the
	// toolchain's default.
	WorkerCPU       string
	WorkerMemory    string
	WorkerDeadlineS int
	// AuthorDeadlineS raises the test author Job's active deadline (030 T021; default 1200 s).
	AuthorDeadlineS int
	CacheSize       string // optional override
	MaxInputMB      int
	PublisherEnv    string // token mode: targets/<name>.publisher.env
	SecurityLevel   string // minimal (default) | recommended | strict (roadmap C-14; 018)
	AuthorEnv       string // targets/<name>.author.env: the test author's companion-only token (recommended level)
	AuthorAuto      string // on|off: `./chalkeus forge author watch` may draft this target's items (024)
	FreeModels      string // on|off: the worker and author may use OpenCode's free models (opt-in)
	// SliceRuns on|off (026): step mode and automatic drafting work an item slice by slice. Off
	// (the default) they build every item whole, as before; `run --slice` works either way.
	SliceRuns       string
	AuthorIntervalS int    // seconds between the watcher's polls (024, default 120)
	AuthorAttempts  int    // author Jobs per automatic draft (024, default 2, at most 3)
	AuthorModel     string // 041: the test author's model ("" = the global setting, then the worker's)
	ProposeLabel    string // the label that proposes an item to step mode (021; default DefaultProposeLabel)
	// ProposeLabelDefault is true when the profile sets no label, so step mode uses the default
	// (and says so if issues still carry OldProposeLabel, 027 FR-007).
	ProposeLabelDefault bool
	StepIntervalS       int // seconds between step mode's passes (021, default 120)
	Fixture             bool
	// 037: the Git host. SCM "" is GitHub (every existing profile); SCMHost names a self-managed
	// GitLab ("" = gitlab.com); SCMCABundle is the absolute path of its CA bundle, or "".
	SCM         scm.Kind
	SCMHost     string
	SCMCABundle string
}

// Security levels (roadmap C-14): who may write the target and read the companion.
const (
	LevelMinimal     = "minimal"
	LevelRecommended = "recommended"
	LevelStrict      = "strict"
)

// AuthorToken reads PILOT_AUTHOR_TOKEN from the target's author.env (mode 0600), the test
// author's companion-only credential at the recommended level. Never printed.
func (t Target) AuthorToken() (string, error) {
	if err := CheckMode(t.AuthorEnv); err != nil {
		return "", targetErr("TARGET_MODE", "%s", err.Error())
	}
	raw, err := os.ReadFile(t.AuthorEnv)
	if err != nil {
		return "", targetErr("TARGET_INVALID", "the recommended level needs %s with FORGE_AUTHOR_TOKEN (a token that can write only the companion)", t.AuthorEnv)
	}
	tok := strings.TrimSpace(ParseSettings(string(raw), t.AuthorEnv)["PILOT_AUTHOR_TOKEN"])
	if tok == "" {
		return "", targetErr("TARGET_INVALID", "%s has no FORGE_AUTHOR_TOKEN", t.AuthorEnv)
	}
	return tok, nil
}

var companionPathRE = regexp.MustCompile(`^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*$`)

func companionPathOK(p string) bool {
	if !companionPathRE.MatchString(p) {
		return false
	}
	for _, part := range strings.Split(p, "/") {
		if part == "." || part == ".." {
			return false
		}
	}
	return true
}

// CompanionItemDir is where an item's hidden tests live inside the companion checkout
// (slash-separated): [<PILOT_COMPANION_PATH>/]items/<item>.
func (t Target) CompanionItemDir(item string) string {
	if t.CompanionPath == "" {
		return "items/" + item
	}
	return t.CompanionPath + "/items/" + item
}

// CompanionSliceDir is where one slice's hidden tests live (026, contracts/slices.md):
// [<PILOT_COMPANION_PATH>/]items/<item>/<slice>.
func (t Target) CompanionSliceDir(item, slice string) string {
	return t.CompanionItemDir(item) + "/" + slice
}

// SliceLayout decides whether an item's companion folder uses the per-slice layout: every
// top-level entry is a directory named after one of the item's slice ids. entries maps each
// top-level name to whether it is a directory. With no entries, or when no entry is a slice
// folder, the layout is the flat one (today's). stray lists the entries that break a per-slice
// layout (a mixed layout, refused by readiness).
func SliceLayout(entries map[string]bool, sliceIDs []string) (perSlice bool, stray []string) {
	ids := map[string]bool{}
	for _, id := range sliceIDs {
		ids[id] = true
	}
	slices := 0
	for name, isDir := range entries {
		if isDir && ids[name] {
			slices++
		} else {
			stray = append(stray, name)
		}
	}
	sort.Strings(stray)
	if slices == 0 {
		return false, nil
	}
	return true, stray
}

var changeTypes = map[string]bool{"feat": true, "fix": true, "refactor": true, "perf": true, "test": true,
	"docs": true, "build": true, "ci": true, "style": true, "chore": true}

// TargetsDir is ConfigDir/targets.
func (c *Config) TargetsDir() string { return filepath.Join(c.ConfigDir, "targets") }

// Fixture is the implicit fixture target (today's single-repository pilot.env).
func (c *Config) Fixture() Target {
	t := Target{Name: FixtureTarget, Repo: c.Repo(), Branch: c.Branch(), Toolchain: "python",
		GithubIssues: c.Values["PILOT_GITHUB_ISSUES"], GithubApprovals: c.Values["PILOT_GITHUB_APPROVALS"],
		MaxInputMB: 50, PublisherEnv: c.PublisherEnv, Fixture: true}
	if h := c.FixtureHost(); !h.IsGitHub() { // 037: GitHub keeps SCM "" as before
		t.SCM, t.SCMCABundle = h.Kind, h.CABundle
		if h.Kind == scm.GitLab {
			t.SCMHost = strings.TrimSpace(c.Values["PILOT_SCM_HOST"])
		}
	}
	return t
}

func targetErr(code, format string, a ...any) *Error {
	e := errf(2, format, a...)
	e.Msg = code + ": " + e.Msg
	return e
}

// ListTargets returns the configured target names, sorted ("fixture" is implicit and not listed).
func (c *Config) ListTargets() []string {
	m, _ := filepath.Glob(filepath.Join(c.TargetsDir(), "*.env"))
	var out []string
	for _, p := range m {
		n := strings.TrimSuffix(filepath.Base(p), ".env")
		if strings.HasSuffix(n, ".publisher") || !targetNameRE.MatchString(n) || n == FixtureTarget {
			continue
		}
		out = append(out, n)
	}
	sort.Strings(out)
	return out
}

// LoadTarget reads and validates targets/<name>.env. "" or "fixture" is the fixture target.
// origin is this checkout's origin (the canary); it may be "".
// DefaultProposeLabel proposes an item to step mode when a profile sets no label (027 FR-007).
// OldProposeLabel was the default before 027.
const (
	DefaultProposeLabel = "chalkeus:proposed"
	OldProposeLabel     = "pilot/go"
)

func (c *Config) LoadTarget(name, origin string) (Target, error) {
	if name == "" || name == FixtureTarget {
		return c.Fixture(), nil
	}
	if !targetNameRE.MatchString(name) {
		return Target{}, targetErr("TARGET_INVALID", "target name %q must match %s", name, targetNameRE)
	}
	dir := c.TargetsDir()
	p := filepath.Join(dir, name+".env")
	if _, err := os.Stat(p); err != nil {
		return Target{}, targetErr("TARGET_UNKNOWN", "no target %q: create %s (see docs/targets.md)", name, p)
	}
	if st, err := os.Stat(dir); err == nil && st.Mode().Perm()&0o077 != 0 {
		return Target{}, targetErr("TARGET_MODE", "%s must be mode 0700 (is 0o%o)", dir, st.Mode().Perm())
	}
	if err := CheckMode(p); err != nil {
		return Target{}, targetErr("TARGET_MODE", "%s", err.Error())
	}
	raw, err := os.ReadFile(p)
	if err != nil {
		return Target{}, err
	}
	t, err := parseTarget(name, ParseSettings(string(raw), p), c)
	if err != nil {
		return Target{}, err
	}
	t.PublisherEnv = filepath.Join(dir, name+".publisher.env")
	t.AuthorEnv = filepath.Join(dir, name+".author.env")
	if err := c.checkCanary(t, origin); err != nil {
		return Target{}, err
	}
	return t, nil
}

func parseTarget(name string, v map[string]string, c *Config) (Target, error) {
	invalid := func(key, why string) error {
		return targetErr("TARGET_INVALID", "targets/%s.env: %s", name, settingMsg(key, why))
	}
	t := Target{Name: name, Repo: v["PILOT_TARGET_REPO"], Branch: v["PILOT_TARGET_BRANCH"], Toolchain: v["PILOT_TOOLCHAIN"],
		ToolchainImage: v["PILOT_TOOLCHAIN_IMAGE"],
		TestCommand:    strings.TrimSpace(v["PILOT_TEST_COMMAND"]), CompanionRepo: v["PILOT_COMPANION_REPO"],
		CompanionPath:  strings.Trim(strings.TrimSpace(v["PILOT_COMPANION_PATH"]), "/"),
		InstallCommand: strings.TrimSpace(v["PILOT_INSTALL_COMMAND"]), ChangeType: v["PILOT_CHANGE_TYPE"],
		GithubIssues: v["PILOT_GITHUB_ISSUES"], GithubApprovals: v["PILOT_GITHUB_APPROVALS"],
		GraderMemory: v["PILOT_GRADER_MEMORY"], CacheSize: v["PILOT_CACHE_SIZE"], MaxInputMB: 50,
		WorkerCPU: strings.TrimSpace(v["PILOT_WORKER_CPU"]), WorkerMemory: strings.TrimSpace(v["PILOT_WORKER_MEMORY"]),
		AuthorAuto: strings.TrimSpace(v["PILOT_AUTHOR_AUTO"]), AuthorIntervalS: 120, AuthorAttempts: 2,
		SliceRuns: strings.TrimSpace(v["PILOT_SLICE_RUNS"]), FreeModels: strings.TrimSpace(v["PILOT_ALLOW_FREE_MODELS"]),
		ProposeLabel: strings.TrimSpace(v["PILOT_PROPOSE_LABEL"]), StepIntervalS: 120,
		AuthorModel: strings.TrimSpace(v["PILOT_AUTHOR_MODEL"])}
	kind, key, why := scmSyntax(v)
	if key != "" {
		return Target{}, invalid(key, why)
	}
	if kind != scm.GitHub {
		t.SCM, t.SCMHost = kind, strings.TrimSpace(v["PILOT_SCM_HOST"])
		if c != nil {
			ca, err := caBundlePath(c.ConfigDir, v["PILOT_SCM_CA_BUNDLE"])
			if err != nil {
				return Target{}, targetErr("TARGET_INVALID", "targets/%s.env: %s", name, err.Error())
			}
			t.SCMCABundle = ca
		}
	}
	if err := scm.ValidRepo(kind, t.Repo); err != nil {
		return Target{}, invalid("PILOT_TARGET_REPO", err.Error())
	}
	if t.Branch == "" {
		t.Branch = "main"
	}
	if t.ToolchainImage != "" && !digestRefRE.MatchString(t.ToolchainImage) {
		return Target{}, invalid("PILOT_TOOLCHAIN_IMAGE", "must be pinned by digest: registry/name@sha256:<64 hex>")
	}
	if t.Toolchain == "" && t.ToolchainImage != "" {
		t.Toolchain = "operator-supplied"
	}
	if t.Toolchain == "" {
		return Target{}, invalid("PILOT_TOOLCHAIN", "is required (a name from pilot/images/toolchains.json, or set FORGE_TOOLCHAIN_IMAGE to your own image)")
	}
	if t.TestCommand == "" {
		return Target{}, invalid("PILOT_TEST_COMMAND", "is required")
	}
	if err := scm.ValidRepo(kind, t.CompanionRepo); err != nil { // the companion is on the target's host (037)
		return Target{}, invalid("PILOT_COMPANION_REPO", err.Error())
	}
	if t.CompanionPath != "" && !companionPathOK(t.CompanionPath) {
		return Target{}, invalid("PILOT_COMPANION_PATH", "must be a relative folder of letters, digits, '.', '_', '-' and '/', without '..'")
	}
	if strings.EqualFold(t.CompanionRepo, t.Repo) {
		return Target{}, invalid("PILOT_COMPANION_REPO", "must differ from FORGE_TARGET_REPO")
	}
	for _, h := range splitList(v["PILOT_REGISTRY_HOSTS"], false) {
		if !hostRE.MatchString(h) {
			return Target{}, invalid("PILOT_REGISTRY_HOSTS", "entries must be hostnames, got "+h)
		}
		t.RegistryHosts = append(t.RegistryHosts, h)
	}
	if t.InstallCommand != "" && len(t.RegistryHosts) == 0 {
		return Target{}, invalid("PILOT_INSTALL_COMMAND", "needs FORGE_REGISTRY_HOSTS: dependencies are downloaded from the registries you list")
	}
	for _, g := range splitList(v["PILOT_TEST_PATHS"], false) {
		if strings.HasPrefix(g, "/") || strings.Contains(g, "..") {
			return Target{}, invalid("PILOT_TEST_PATHS", "entries must be relative globs inside the repository, got "+g)
		}
		t.TestPaths = append(t.TestPaths, g)
	}
	t.SecurityLevel = strings.TrimSpace(v["PILOT_SECURITY_LEVEL"])
	if t.SecurityLevel == "" {
		t.SecurityLevel = LevelMinimal
	}
	if t.SecurityLevel != LevelMinimal && t.SecurityLevel != LevelRecommended && t.SecurityLevel != LevelStrict {
		return Target{}, invalid("PILOT_SECURITY_LEVEL", "must be minimal, recommended or strict")
	}
	if t.ChangeType == "" {
		t.ChangeType = "feat"
	}
	if !changeTypes[t.ChangeType] {
		return Target{}, invalid("PILOT_CHANGE_TYPE", "must be a Conventional Commits type: feat, fix, refactor, perf, test, docs, build, ci, style or chore")
	}
	if t.GithubIssues == "" {
		t.GithubIssues = "off" // a new target opts in (014 R14)
	}
	if t.GithubApprovals == "" && c != nil && kind == scm.GitHub { // 037: the loop is GitHub-only; other hosts don't inherit it
		t.GithubApprovals = c.Values["PILOT_GITHUB_APPROVALS"]
	}
	if t.GithubApprovals == "" {
		t.GithubApprovals = "off"
	}
	if t.AuthorAuto == "" {
		t.AuthorAuto = "off" // auto-draft is opt-in per target (024 FR-001)
	}
	if t.SliceRuns == "" {
		t.SliceRuns = "off" // slice-by-slice step mode is opt-in per target (026 FR-005)
	}
	if t.FreeModels == "" {
		t.FreeModels = "off" // the worker image disables OpenCode's free models; a target opts in
	}
	for k, x := range map[string]string{"PILOT_GITHUB_ISSUES": t.GithubIssues, "PILOT_GITHUB_APPROVALS": t.GithubApprovals, "PILOT_AUTHOR_AUTO": t.AuthorAuto, "PILOT_SLICE_RUNS": t.SliceRuns, "PILOT_ALLOW_FREE_MODELS": t.FreeModels} {
		if x != "on" && x != "off" {
			return Target{}, invalid(k, "must be on or off")
		}
	}
	if t.WorkerCPU != "" && !cpuRE.MatchString(t.WorkerCPU) {
		return Target{}, invalid("PILOT_WORKER_CPU", "must be a CPU quantity like 2, 1.5 or 3500m")
	}
	for k, x := range map[string]string{"PILOT_GRADER_MEMORY": t.GraderMemory, "PILOT_CACHE_SIZE": t.CacheSize, "PILOT_WORKER_MEMORY": t.WorkerMemory} {
		if x != "" && !quantityRE.MatchString(x) {
			return Target{}, invalid(k, "must be a quantity like 2Gi or 512Mi")
		}
	}
	for k, dst := range map[string]*int{"PILOT_GRADER_DEADLINE_S": &t.GraderDeadlineS, "PILOT_MAX_INPUT_MB": &t.MaxInputMB,
		"PILOT_WORKER_DEADLINE_S": &t.WorkerDeadlineS, "PILOT_AUTHOR_DEADLINE_S": &t.AuthorDeadlineS,
		"PILOT_AUTHOR_INTERVAL_S": &t.AuthorIntervalS, "PILOT_AUTHOR_AUTO_ATTEMPTS": &t.AuthorAttempts,
		"PILOT_STEP_INTERVAL_S": &t.StepIntervalS} {
		if x := v[k]; x != "" {
			n, err := strconv.Atoi(x)
			if err != nil || n <= 0 {
				return Target{}, invalid(k, "must be a positive integer")
			}
			*dst = n
		}
	}
	if t.AuthorAttempts > 3 {
		return Target{}, invalid("PILOT_AUTHOR_AUTO_ATTEMPTS", "must be 1, 2 or 3")
	}
	if t.ProposeLabel == "" {
		t.ProposeLabel, t.ProposeLabelDefault = DefaultProposeLabel, true
	}
	if len(t.ProposeLabel) > 50 || strings.ContainsAny(t.ProposeLabel, ",\n") {
		return Target{}, invalid("PILOT_PROPOSE_LABEL", "must be a GitHub label name (at most 50 characters, no commas)")
	}
	if t.StepIntervalS < 30 {
		return Target{}, invalid("PILOT_STEP_INTERVAL_S", "must be at least 30 (seconds)")
	}
	if t.AuthorIntervalS < 30 {
		return Target{}, invalid("PILOT_AUTHOR_INTERVAL_S", "must be at least 30 (seconds)")
	}
	return t, nil
}

// checkCanary refuses a target that is this checkout's origin or another target's companion.
func (c *Config) checkCanary(t Target, origin string) error {
	if origin != "" && (strings.EqualFold(t.Repo, origin) || strings.EqualFold(t.CompanionRepo, origin)) {
		return targetErr("TARGET_IS_CANARY", "%s is this repository's origin (the write probe's canary)", origin)
	}
	for _, other := range c.ListTargets() {
		if other == t.Name {
			continue
		}
		raw, err := os.ReadFile(filepath.Join(c.TargetsDir(), other+".env"))
		if err != nil {
			continue
		}
		v := ParseSettings(string(raw), filepath.Join(c.TargetsDir(), other+".env"))
		if strings.EqualFold(v["PILOT_COMPANION_REPO"], t.Repo) {
			return targetErr("TARGET_IS_CANARY", "%s is target %q's companion repository; hidden tests must never be a build target", t.Repo, other)
		}
	}
	return nil
}
