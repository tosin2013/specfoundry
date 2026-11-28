package author

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"

	"github.com/google/go-github/v85/github"

	"github.com/tosin2013/chalkeus/internal/ghloop"
)

// Submit is `./chalkeus forge author submit` (018 T011): only a draft whose last check passed, unchanged
// since; one pull request on the companion, adding the files under the item's folder. A human
// merges it.
func Submit(ctx context.Context, e Env, item string) (*Draft, error) {
	d, err := LoadDraft(Root(e.EvidenceRoot), "", e.Target.Name, item)
	if err != nil {
		return nil, err
	}
	if d.State == "submitted" {
		return d, fmt.Errorf("draft %s was already submitted: %v", d.ID, d.PR["url"])
	}
	draftDir := filepath.Join(d.Workspace, "draft")
	files, hash, err := DraftFiles(draftDir)
	if err != nil {
		return d, err
	}
	if len(d.Checks) == 0 || d.Checks[len(d.Checks)-1].Result != CodeDraftOK || d.Checks[len(d.Checks)-1].DraftHash != hash {
		return d, refuse(CodeDraftNotChecked, "the draft changed since its last passing check, or never passed one; run ./chalkeus forge author check first")
	}
	id, err := e.Identity(ctx, e.Target)
	if err != nil {
		return d, err
	}
	if open, err := e.OpenAuthorPRs(ctx, id, d.Companion, branchPrefix(item)); err != nil {
		return d, err
	} else if len(open) > 0 {
		return d, refuse(CodeDraftPROpen, "a draft pull request is already open on %s (%s)", d.Companion, strings.Join(open, ", "))
	}
	spec, _ := os.ReadFile(filepath.Join(d.Workspace, "spec.md"))
	var m Map
	raw, _ := os.ReadFile(filepath.Join(draftDir, MapFile))
	_ = json.Unmarshal(raw, &m)
	pr, commit, err := openPR(ctx, id.Client, d, draftDir, append(files, File{Path: MapFile}), replaceOn(d),
		fmt.Sprintf("test(%s): hidden acceptance tests for %s", item, d.Title), PRBody(d, Criteria(string(spec)), m))
	if err != nil {
		_ = d.Event("submit_error", clip(err.Error()))
		return d, err
	}
	d.Files, d.State = files, "submitted"
	d.PR = map[string]any{"url": pr.GetHTMLURL(), "number": pr.GetNumber(), "branch": pr.GetHead().GetRef(), "commit": commit, "identity": id.Login}
	_ = d.Save()
	_ = d.Event("submitted", fmt.Sprintf("pr=%s commit=%s files=%d", pr.GetHTMLURL(), commit, len(files)))
	fmt.Fprintf(e.Out, "opened %s\nA human reviews and merges it; then the item's run can start.\n", pr.GetHTMLURL())
	return d, nil
}

func replaceOn(d *Draft) bool { b, _ := d.Readiness["replace"].(bool); return b }

// PRBody describes the draft: target, item, spec hash, level, identity, the passing check and
// the coverage table. It never contains a test file's contents.
func PRBody(d *Draft, criteria []Criterion, m Map) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Hidden acceptance tests for **%s** item **%s**: %s\n\n", d.Repo, d.Item, d.Title)
	fmt.Fprintf(&b, "- Drafted by the test author (Chalkeus 018), level `%s`, identity `%s`.\n", d.Level, d.Identity)
	if d.Model != "" {
		fmt.Fprintf(&b, "- Drafted by: `%s` (041).\n", d.Model)
	}
	last := d.Checks[len(d.Checks)-1]
	fmt.Fprintf(&b, "- Checked on the unchanged base `%s`: the project's tests pass and these tests fail (`%s`, draft `%s`).\n", short(d.BaseRevision), last.Result, short(last.DraftHash))
	fmt.Fprintf(&b, "- Spec SHA-256 `%s`.\n- Files only under `%s/`.\n\n", short(d.SpecSHA256), d.CompanionDir)
	b.WriteString("## Coverage\n\n| Criterion | | Tests |\n|---|---|---|\n")
	for _, c := range criteria {
		refs := m.Criteria[c.ID]
		cell := "**uncovered**"
		if len(refs) > 0 {
			cell = "`" + strings.Join(refs, "`<br>`") + "`"
		}
		fmt.Fprintf(&b, "| %s | %s | %s |\n", c.ID, strings.ReplaceAll(c.Title, "|", "/"), cell)
	}
	b.WriteString("\n**Review before merging:** merging is the approval. Build workers never see these tests; keep this repository's access limited to test authors.\n")
	return b.String()
}

func short(s string) string {
	if len(s) > 12 {
		return s[:12]
	}
	return s
}

// openPR writes the files as one commit on a new branch through the Git Data API and opens the
// pull request. With replace, files under the item folder that aren't in the draft are deleted.
func openPR(ctx context.Context, c *github.Client, d *Draft, draftDir string, files []File, replace bool, title, body string) (*github.PullRequest, string, error) {
	owner, name := ghloop.SplitRepo(d.Companion)
	repo, _, err := c.Repositories.Get(ctx, owner, name)
	if err != nil {
		return nil, "", err
	}
	baseBranch := repo.GetDefaultBranch()
	ref, _, err := c.Git.GetRef(ctx, owner, name, "refs/heads/"+baseBranch)
	if err != nil {
		return nil, "", err
	}
	parent := ref.GetObject().GetSHA()
	pc, _, err := c.Git.GetCommit(ctx, owner, name, parent)
	if err != nil {
		return nil, "", err
	}
	var entries []*github.TreeEntry
	keep := map[string]bool{}
	sort.Slice(files, func(i, j int) bool { return files[i].Path < files[j].Path })
	for _, f := range files {
		raw, err := os.ReadFile(filepath.Join(draftDir, filepath.FromSlash(f.Path)))
		if err != nil {
			return nil, "", err
		}
		blob, _, err := c.Git.CreateBlob(ctx, owner, name, github.Blob{Content: github.Ptr(string(raw)), Encoding: github.Ptr("utf-8")})
		if err != nil {
			return nil, "", err
		}
		p := path.Join(d.CompanionDir, f.Path)
		keep[p] = true
		entries = append(entries, &github.TreeEntry{Path: github.Ptr(p), Mode: github.Ptr("100644"), Type: github.Ptr("blob"), SHA: blob.SHA})
	}
	if replace {
		tree, _, err := c.Git.GetTree(ctx, owner, name, pc.GetTree().GetSHA(), true)
		if err != nil {
			return nil, "", err
		}
		for _, te := range tree.Entries {
			p := te.GetPath()
			if te.GetType() == "blob" && strings.HasPrefix(p, d.CompanionDir+"/") && !keep[p] {
				entries = append(entries, &github.TreeEntry{Path: github.Ptr(p), Mode: github.Ptr("100644"), Type: github.Ptr("blob")})
			}
		}
	}
	tree, _, err := c.Git.CreateTree(ctx, owner, name, pc.GetTree().GetSHA(), entries)
	if err != nil {
		return nil, "", err
	}
	commit, _, err := c.Git.CreateCommit(ctx, owner, name, github.Commit{Message: github.Ptr(title), Tree: tree,
		Parents: []*github.Commit{{SHA: github.Ptr(parent)}}}, nil)
	if err != nil {
		return nil, "", err
	}
	branch := branchPrefix(d.Item) + strings.ToLower(d.ID)
	if _, _, err := c.Git.CreateRef(ctx, owner, name, github.CreateRef{Ref: "refs/heads/" + branch, SHA: commit.GetSHA()}); err != nil {
		return nil, "", err
	}
	pr, _, err := c.PullRequests.Create(ctx, owner, name, &github.NewPullRequest{Title: github.Ptr(title), Head: github.Ptr(branch),
		Base: github.Ptr(baseBranch), Body: github.Ptr(body)})
	if err != nil {
		return nil, "", err
	}
	return pr, commit.GetSHA(), nil
}

// OpenAuthorPRs lists the companion's open PRs whose head branch starts with prefix.
func OpenAuthorPRs(ctx context.Context, id *Identity, repo, prefix string) ([]string, error) {
	owner, name := ghloop.SplitRepo(repo)
	prs, _, err := id.Client.PullRequests.List(ctx, owner, name, &github.PullRequestListOptions{State: "open", ListOptions: github.ListOptions{PerPage: 100}})
	if err != nil {
		return nil, err
	}
	var out []string
	for _, p := range prs {
		if strings.HasPrefix(p.GetHead().GetRef(), prefix) {
			out = append(out, p.GetHTMLURL())
		}
	}
	return out, nil
}
