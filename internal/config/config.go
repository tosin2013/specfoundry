// Package config is the operator configuration (reference: the former Python pilot's config.py;
// specs/002-m1-gated-pilot/contracts/config.md, amended by 004).
package config

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/tosin2013/chalkeus/internal/pyrepr"
	"github.com/tosin2013/chalkeus/internal/verbose"

	"github.com/tosin2013/chalkeus/internal/names"
)

// Error is a configuration problem; Code is the CLI exit code (2 error, 3 repo guard).
type Error struct {
	Msg  string
	Code int
}

func (e *Error) Error() string { return e.Msg }

// ExitCode lets the CLI map the error to its exit code.
func (e *Error) ExitCode() int { return e.Code }

func errf(code int, format string, a ...any) *Error {
	return &Error{Msg: fmt.Sprintf(format, a...), Code: code}
}

var (
	scmNameRE     = regexp.MustCompile(`(?i)GITHUB|^GH_|GIT_.*TOKEN|GITLAB|BITBUCKET|GLPAT`) // 037: other hosts' names
	refRE         = regexp.MustCompile(`^\{(file|env):[^}]+\}$`)
	secretFieldRE = regexp.MustCompile(`(?i)key|token|secret|password`)
	repoRE        = regexp.MustCompile(`^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$`)
	originRE      = regexp.MustCompile(`github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$`)
)

// Defaults and required keys, as in the reference.
var (
	Defaults = map[string]string{
		"PILOT_FIXTURE_BRANCH":        "main",
		"PILOT_SPEND_CAP_USD":         "1.00",
		"PILOT_TOKEN_CAP":             "2000000",
		"PILOT_PROVIDER_CAP_DECLARED": "false",
		"RETRY_LIMIT":                 "2",
		"PILOT_GITHUB_ISSUES":         "off",
		"PILOT_GITHUB_APPROVALS":      "off",
	}
	Required = []string{"PILOT_FIXTURE_REPO", "PILOT_MODEL", "PILOT_MODEL_EGRESS_HOSTS"}
)

const guide = "docs/operator-guide.md"

var missingHints = map[string]string{
	"pilot.env":      "create it first: " + guide + ", section 5 (Configure your model provider)",
	"forge.env":      "create it first: " + guide + ", section 5 (Configure your model provider)",
	"publisher.env":  "store the token first: ./chalkeus forge publisher-token",
	"github-app.pem": "store the App key first: ./chalkeus forge app-key < <app>.private-key.pem (docs/github-app.md)",
	"opencode":       "create it first: " + guide + ", section 5 (Configure your model provider)",
}

func missingHint(path string) string {
	if h, ok := missingHints[filepath.Base(path)]; ok {
		return "\n  " + h
	}
	return ""
}

// Config is the loaded operator configuration.
type Config struct {
	Values       map[string]string
	ConfigDir    string
	ModelDir     string
	PublisherEnv string
}

// Get returns a value ("" if unset).
func (c *Config) Get(k string) string { return c.Values[k] }

func (c *Config) Repo() string          { return c.Values["PILOT_FIXTURE_REPO"] }
func (c *Config) Branch() string        { return c.Values["PILOT_FIXTURE_BRANCH"] }
func (c *Config) RetryLimit() int       { n, _ := strconv.Atoi(c.Values["RETRY_LIMIT"]); return n }
func (c *Config) AppKey() string        { return filepath.Join(c.ConfigDir, "github-app.pem") }
func (c *Config) GithubApprovals() bool { return c.Values["PILOT_GITHUB_APPROVALS"] == "on" }

// GithubIssues is on when PILOT_GITHUB_ISSUES=on or GitHub approvals are on (004).
func (c *Config) GithubIssues() bool {
	return c.Values["PILOT_GITHUB_ISSUES"] == "on" || c.GithubApprovals()
}

// ModelHosts lists the model egress hosts.
func (c *Config) ModelHosts() []string { return splitList(c.Values["PILOT_MODEL_EGRESS_HOSTS"], false) }

// Approvers lists GitHub logins allowed to approve (a leading @ is dropped).
func (c *Config) Approvers() []string { return splitList(c.Values["PILOT_APPROVERS"], true) }

func splitList(s string, dropAt bool) []string {
	var out []string
	for _, x := range strings.Split(s, ",") {
		x = strings.TrimSpace(x)
		if dropAt {
			x = strings.TrimLeft(x, "@")
		}
		if x != "" {
			out = append(out, x)
		}
	}
	return out
}

func exists(p string) bool { _, err := os.Stat(p); return err == nil }

// Credential is `token` or `app` (004 FR-016); it refuses to guess when both exist.
func (c *Config) Credential() (string, error) {
	if v := c.Values["PILOT_PUBLISHER_CREDENTIAL"]; v != "" {
		return v, nil
	}
	if exists(c.AppKey()) && exists(c.PublisherEnv) {
		return "", errf(2, "both a publisher token and a GitHub App key exist: set FORGE_PUBLISHER_CREDENTIAL=token or =app in forge.env")
	}
	if exists(c.AppKey()) {
		return "app", nil
	}
	return "token", nil
}

// ModelFiles are opencode.json plus every *_api_key file (backups ignored).
func (c *Config) ModelFiles() []string { return ModelFiles(c.ModelDir) }

// Public are values safe for the committed evidence: model hosts are hashed.
func (c *Config) Public() map[string]string {
	v := map[string]string{}
	for k, x := range c.Values {
		v[k] = x
	}
	if v["PILOT_MODEL_EGRESS_HOSTS"] != "" {
		var hs []string
		for _, h := range c.ModelHosts() {
			sum := sha256.Sum256([]byte(h))
			hs = append(hs, "sha256:"+hex.EncodeToString(sum[:])[:16])
		}
		v["PILOT_MODEL_EGRESS_HOSTS"] = strings.Join(hs, ",")
	}
	return v
}

// Dir is the operator's config folder (027 FR-005, FR-006): $CHALKEUS_CONFIG, else
// ~/.config/chalkeus when it exists, else the old $SPECFOUNDRY_CONFIG or ~/.config/specfoundry
// (each with a one-time notice saying how to move it), else ~/.config/chalkeus. It never moves,
// copies or creates anything.
func Dir() string {
	if d := os.Getenv("CHALKEUS_CONFIG"); d != "" {
		if os.Getenv("SPECFOUNDRY_CONFIG") != "" {
			names.Notice("folder-env-both", "CHALKEUS_CONFIG is set and wins; SPECFOUNDRY_CONFIG is ignored (remove it)")
		}
		return d
	}
	if d := os.Getenv("SPECFOUNDRY_CONFIG"); d != "" {
		names.Notice("folder-env-old:"+d, "SPECFOUNDRY_CONFIG is the old name of CHALKEUS_CONFIG; it still works, but rename it")
		return d
	}
	home, _ := os.UserHomeDir()
	cur, old := filepath.Join(home, ".config", "chalkeus"), filepath.Join(home, ".config", "specfoundry")
	if exists(cur) {
		if exists(old) {
			names.Notice("folder-both:"+old, "using "+cur+"; the old "+old+" is still there: remove it once you have checked nothing in it is still needed")
		}
		return cur
	}
	if exists(old) {
		names.Notice("folder-old:"+old, "using the old config folder "+old+". Move it once, keeping its permissions: mv "+old+" "+cur)
		return old
	}
	return cur
}

// SettingsFile is the config folder's main settings file: forge.env, else the old pilot.env, else
// forge.env (the name a new file gets). Both present: forge.env wins, with a notice.
func SettingsFile(d string) string {
	cur, old := filepath.Join(d, "forge.env"), filepath.Join(d, "pilot.env")
	switch {
	case exists(cur) && exists(old):
		names.Notice("settings-both:"+d, "both forge.env and pilot.env are in "+d+"; forge.env wins and pilot.env is ignored (remove it)")
		return cur
	case exists(old):
		names.Notice("settings-old:"+d, "pilot.env is the old name of forge.env; it still works, but rename it: mv "+old+" "+cur)
		return old
	}
	return cur
}

// ParseSettings parses a settings file's text and maps FORGE_* keys to the pilot's names
// (names.Canonical); file names it in notices.
func ParseSettings(text, file string) map[string]string {
	return names.Canonical(ParseEnv(text), file)
}

// CheckMode requires the file to exist with no group/other permission bits.
func CheckMode(path string) error {
	st, err := os.Stat(path)
	if err != nil {
		return errf(2, "missing config file: %s%s", path, missingHint(path))
	}
	if m := st.Mode().Perm(); m&0o077 != 0 {
		return errf(2, "%s must be mode 0600 (is 0o%o)", path, m)
	}
	return nil
}

// ParseEnv parses KEY=VALUE lines: comments, inline " #" comments and quotes stripped.
func ParseEnv(text string) map[string]string {
	out := map[string]string{}
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") || !strings.Contains(line, "=") {
			continue
		}
		k, v, _ := strings.Cut(line, "=")
		v, _, _ = strings.Cut(v, " #")
		v = strings.Trim(strings.Trim(strings.TrimSpace(v), `"`), "'")
		out[strings.TrimSpace(k)] = v
	}
	return out
}

// ModelFiles lists opencode.json plus every regular *_api_key file in d, sorted.
func ModelFiles(d string) []string {
	out := []string{filepath.Join(d, "opencode.json")}
	m, _ := filepath.Glob(filepath.Join(d, "*_api_key"))
	sort.Strings(m)
	for _, p := range m {
		if st, err := os.Stat(p); err == nil && st.Mode().IsRegular() {
			out = append(out, p)
		}
	}
	return out
}

// CheckModelDir validates the worker's OpenCode config directory.
func CheckModelDir(d string) error {
	st, err := os.Stat(d)
	if err != nil || !st.IsDir() {
		return errf(2, "missing worker OpenCode config dir: %s%s", d, missingHint(d))
	}
	if st.Mode().Perm()&0o077 != 0 {
		return errf(2, "%s must be mode 0700", d)
	}
	files := ModelFiles(d)
	for _, f := range files {
		if err := CheckMode(f); err != nil {
			return err
		}
		if scmNameRE.MatchString(filepath.Base(f)) {
			return errf(2, "%s: SCM-like credential name; SCM credentials must never reach a worker", filepath.Base(f))
		}
	}
	if len(files) < 2 {
		return errf(2, "%s needs opencode.json and at least one <provider>_api_key file", d)
	}
	raw, err := os.ReadFile(filepath.Join(d, "opencode.json"))
	if err != nil {
		return errf(2, "%s/opencode.json: %v", d, err)
	}
	var doc any
	if err := json.Unmarshal(raw, &doc); err != nil {
		return errf(2, "%s/opencode.json is not valid JSON: %v", d, err)
	}
	return walk(doc, "")
}

func walk(o any, path string) error {
	switch x := o.(type) {
	case map[string]any:
		keys := make([]string, 0, len(x))
		for k := range x {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			if s, ok := x[k].(string); ok && secretFieldRE.MatchString(k) && !refRE.MatchString(s) {
				return errf(2, "opencode.json %s%s must be a {file:...} reference, not a literal secret", path, k)
			}
			if err := walk(x[k], path+k+"."); err != nil {
				return err
			}
		}
	case []any:
		for _, e := range x {
			if err := walk(e, path); err != nil {
				return err
			}
		}
	}
	return nil
}

// OriginRepo returns owner/name of this checkout's GitHub origin, or "".
func OriginRepo(root string) string {
	out, err := exec.Command("git", "-C", root, "remote", "get-url", "origin").Output()
	if err != nil {
		return ""
	}
	m := originRE.FindStringSubmatch(strings.TrimSpace(string(out)))
	if m == nil {
		return ""
	}
	return m[1]
}

// RepoGuard refuses anything but a throwaway "-pilot-fixture" repo that isn't this repo's origin.
func RepoGuard(repo, origin string) error {
	if !repoRE.MatchString(repo) {
		return errf(3, "FORGE_FIXTURE_REPO must be owner/name, got %s", pyrepr.Str(repo))
	}
	_, name, _ := strings.Cut(repo, "/")
	if !strings.HasSuffix(name, "-pilot-fixture") {
		return errf(3, "repo guard: %s does not end in '-pilot-fixture'", repo)
	}
	if origin != "" && strings.EqualFold(repo, origin) {
		return errf(3, "repo guard: %s is this repository's origin", repo)
	}
	return nil
}

// ValidateValues applies defaults and the reference's validation rules.
func ValidateValues(values map[string]string) (map[string]string, error) {
	v := map[string]string{}
	for k, x := range Defaults {
		v[k] = x
	}
	for k, x := range values {
		if x != "" {
			v[k] = x
		}
	}
	var missing []string
	for _, k := range Required {
		if v[k] == "" {
			missing = append(missing, names.Display(k))
		}
	}
	if len(missing) > 0 {
		return nil, errf(2, "forge.env missing %s", pyrepr.Strings(missing))
	}
	rl, err := strconv.Atoi(v["RETRY_LIMIT"])
	if err != nil {
		return nil, errf(2, "RETRY_LIMIT must be an integer")
	}
	if rl < 0 || rl > 2 {
		return nil, errf(2, "RETRY_LIMIT must be between 0 and 2 in M1")
	}
	if _, err := strconv.ParseFloat(strings.TrimSpace(v["PILOT_SPEND_CAP_USD"]), 64); err != nil {
		return nil, errf(2, "FORGE_SPEND_CAP_USD / FORGE_TOKEN_CAP must be numeric")
	}
	if _, err := strconv.Atoi(strings.TrimSpace(v["PILOT_TOKEN_CAP"])); err != nil {
		return nil, errf(2, "FORGE_SPEND_CAP_USD / FORGE_TOKEN_CAP must be numeric")
	}
	for _, k := range []string{"PILOT_GITHUB_ISSUES", "PILOT_GITHUB_APPROVALS"} {
		if v[k] != "on" && v[k] != "off" {
			return nil, errf(2, "%s must be on or off", k)
		}
	}
	if v["PILOT_GITHUB_APPROVALS"] == "on" && len(splitList(v["PILOT_APPROVERS"], false)) == 0 {
		return nil, errf(2, "FORGE_GITHUB_APPROVALS=on needs FORGE_APPROVERS (comma-separated GitHub logins)")
	}
	if _, key, why := scmSyntax(v); key != "" { // 037
		return nil, errf(2, "%s", settingMsg(key, why))
	}
	cred := v["PILOT_PUBLISHER_CREDENTIAL"]
	if cred != "" && cred != "token" && cred != "app" {
		return nil, errf(2, "FORGE_PUBLISHER_CREDENTIAL must be token or app")
	}
	if cred == "app" {
		for _, k := range []string{"PILOT_APP_ID", "PILOT_APP_INSTALLATION_ID"} {
			if _, err := strconv.ParseUint(v[k], 10, 64); err != nil {
				return nil, errf(2, "FORGE_PUBLISHER_CREDENTIAL=app needs a numeric %s", names.Display(k))
			}
		}
	}
	return v, nil
}

// Load reads and validates the configuration. requireSecrets also checks the worker's model
// config and the publisher's credential: publisher.env for a token, github-app.pem for the
// GitHub App (an App-only setup has no publisher.env; found on a fresh Mac in 031); guard
// applies the repo guard against root's origin.
func Load(root string, requireSecrets, guard bool) (*Config, error) {
	d := Dir()
	pilotEnv := SettingsFile(d)
	if err := CheckMode(pilotEnv); err != nil {
		return nil, err
	}
	raw, err := os.ReadFile(pilotEnv)
	if err != nil {
		return nil, err
	}
	values, err := ValidateValues(ParseSettings(string(raw), pilotEnv))
	if err != nil {
		return nil, err
	}
	c := &Config{Values: values, ConfigDir: d, ModelDir: filepath.Join(d, "opencode"), PublisherEnv: filepath.Join(d, "publisher.env")}
	verbose.AddRedaction(c.ModelHosts()...) // the model host is never printed, not even at -vvv
	if requireSecrets {
		if err := CheckModelDir(c.ModelDir); err != nil {
			return nil, err
		}
		cred, err := c.Credential()
		if err != nil {
			return nil, err
		}
		credFile := c.PublisherEnv
		if cred == "app" {
			credFile = c.AppKey()
		}
		if err := CheckMode(credFile); err != nil {
			return nil, err
		}
	}
	if _, err := caBundlePath(d, values["PILOT_SCM_CA_BUNDLE"]); err != nil { // 037
		return nil, err
	}
	if guard {
		kind, _, _ := scmSyntax(values)
		if err := RepoGuardFor(kind, values["PILOT_FIXTURE_REPO"], OriginRepo(root)); err != nil {
			return nil, err
		}
	}
	return c, nil
}

// AuthorModel is the model the test author's Jobs use (041 US1): the target profile's
// FORGE_AUTHOR_MODEL, then forge.env's, then the worker's model (FORGE_MODEL).
func (c *Config) AuthorModel(t Target) string {
	if t.AuthorModel != "" {
		return t.AuthorModel
	}
	if m := strings.TrimSpace(c.Get("PILOT_AUTHOR_MODEL")); m != "" {
		return m
	}
	return c.Get("PILOT_MODEL")
}

// AuthorModelProblem says why the author's model can't be used ("" when it can). Version 1
// shares the worker's provider, key and model egress host (041 research R5), so the provider
// part (before "/") must match the worker's.
func (c *Config) AuthorModelProblem(t Target) string {
	am, wm := c.AuthorModel(t), c.Get("PILOT_MODEL")
	if am == wm {
		return ""
	}
	ap, _, _ := strings.Cut(am, "/")
	wp, _, _ := strings.Cut(wm, "/")
	if ap != wp {
		return fmt.Sprintf("FORGE_AUTHOR_MODEL %s uses provider %s, but the worker's model %s uses %s: the test author shares the worker's provider, key and model host; pick a %s model", am, ap, wm, wp, wp)
	}
	return ""
}
