package cli

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/tosin2013/chalkeus/internal/scm/hosts"
	"io"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/spf13/cobra"

	"github.com/tosin2013/chalkeus/internal/author"
	"github.com/tosin2013/chalkeus/internal/checks"
	"github.com/tosin2013/chalkeus/internal/cluster"
	"github.com/tosin2013/chalkeus/internal/config"
	"github.com/tosin2013/chalkeus/internal/fixture"
	"github.com/tosin2013/chalkeus/internal/gate"
	"github.com/tosin2013/chalkeus/internal/images"
	"github.com/tosin2013/chalkeus/internal/names"
	"github.com/tosin2013/chalkeus/internal/pipeline"
	"github.com/tosin2013/chalkeus/internal/readiness"
	"github.com/tosin2013/chalkeus/internal/slice"
	"github.com/tosin2013/chalkeus/internal/verbose"
)

// authorCmd is `./chalkeus forge author` (018): the test author's helper commands. Only a separate
// test-author session runs these (the test-author skill); the session that drives runs never
// does (the pilot skill).
func authorCmd() *cobra.Command {
	g := &cobra.Command{
		Use:   "author",
		Short: "test author (018): draft an item's hidden tests and open a companion pull request; never run by the session that drives runs",
	}
	mk := func(use, short string, run func(cmd *cobra.Command, e author.Env, item string) error) *cobra.Command {
		c := &cobra.Command{Use: use, Short: short, Args: cobra.NoArgs,
			RunE: func(cmd *cobra.Command, _ []string) error {
				e, item, err := authorEnv(cmd)
				if err != nil {
					return err
				}
				return run(cmd, e, item)
			}}
		addTargetFlag(c)
		c.Flags().String("item", "", "roadmap item NNN of the target")
		requireTarget(c)
		_ = c.MarkFlagRequired("item")
		return c
	}
	start := mk("start", "check the item and create the draft workspace", func(cmd *cobra.Command, e author.Env, item string) error {
		replace, _ := cmd.Flags().GetBool("replace")
		sl, _ := cmd.Flags().GetString("slice")
		e.Slice = slice.Normalize(sl)
		_, err := author.Start(context.Background(), e, item, replace)
		return err
	})
	start.Flags().Bool("replace", false, "propose replacing the item's existing hidden tests (still only a pull request)")
	start.Flags().String("slice", "", "draft the hidden tests of one slice of the item, e.g. US2 (026): they go to items/<item>/<slice>/")
	check := mk("check", "prove on the cluster that the project's tests pass and the drafted tests fail on the unchanged base", func(cmd *cobra.Command, e author.Env, item string) error {
		p, err := pipelineFor(cmd)
		if err != nil {
			return err
		}
		_, err = author.Check(context.Background(), e, item, p.AuthorBaseline)
		return err
	})
	submit := mk("submit", "open the companion pull request for a checked draft", func(cmd *cobra.Command, e author.Env, item string) error {
		_, err := author.Submit(context.Background(), e, item)
		return err
	})
	status := mk("status", "print the latest draft's state and evidence folder", func(cmd *cobra.Command, e author.Env, item string) error {
		d, err := author.LoadDraft(author.Root(e.EvidenceRoot), "", e.Target.Name, item)
		if err != nil {
			return Exit(ExitError, "%v", err)
		}
		raw, _ := json.MarshalIndent(map[string]any{"draft_id": d.ID, "state": d.State, "level": d.Level, "identity": d.Identity,
			"files": len(d.Files), "checks": d.Checks, "mapping": d.Mapping, "pr": d.PR, "evidence": d.Dir(), "workspace": d.Workspace}, "", "  ")
		_, _ = fmt.Fprintln(cmd.OutOrStdout(), string(raw))
		return nil
	})
	g.AddCommand(start, check, submit, status, authorWatchCmd())
	return g
}

// authorWatchCmd is `./chalkeus forge author watch` (024, contracts/author-watch.md): drafts the hidden tests
// of a target's ready items in an isolated author Job, checks them, and opens the companion pull
// request. Only for targets with PILOT_AUTHOR_AUTO=on. The operator starts it in their own
// terminal; the session that drives runs never does.
func authorWatchCmd() *cobra.Command {
	c := &cobra.Command{Use: "watch", Args: cobra.NoArgs,
		Short: "024: draft hidden tests automatically for a target's ready items (FORGE_AUTHOR_AUTO=on); never run by the session that drives runs",
		RunE: func(cmd *cobra.Command, _ []string) error {
			// Unattended work is easier to follow with diagnostics, so `author watch` defaults to
			// -vv (pod phases, events, the author proxy's refusals). -v or PILOT_VERBOSE choose
			// another level; PILOT_VERBOSE=0 silences it. The agent's live stream (-vvv) is never
			// shown for the author: it would print the drafted tests.
			n, _ := cmd.Flags().GetCount("verbose")
			_, envSet := names.LookupEnv("VERBOSE")
			if l := watchVerbosity(n, envSet); l != verbose.Level() {
				verbose.Set(l, cmd.ErrOrStderr())
			}
			e, _, err := authorEnv(cmd)
			if err != nil {
				return err
			}
			if e.Target.AuthorAuto != "on" {
				return Exit(ExitError, "auto-draft is off for target %s: set FORGE_AUTHOR_AUTO=on in its profile to let `author watch` draft its items", e.Target.Name)
			}
			p, err := pipelineFor(cmd)
			if err != nil {
				return err
			}
			w, err := authorWatchEnv(e, p)
			if err != nil {
				return err
			}
			t := e.Target
			ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
			defer stop()
			once, _ := cmd.Flags().GetBool("once")
			if redraft, _ := cmd.Flags().GetBool("redraft"); redraft {
				w.EnableRedraft()
			}
			out := cmd.OutOrStdout()
			fmt.Fprintf(out, "author watch: target %s, every %d s, up to %d author Job(s) per draft; Ctrl-C stops it\n", t.Name, t.AuthorIntervalS, t.AuthorAttempts)
			for {
				res, err := author.Pass(ctx, w)
				if err != nil {
					fmt.Fprintf(out, "author watch: %v\n", err)
					if once {
						return Exit(ExitError, "%v", err)
					}
				}
				if once {
					if res == author.PassFailed {
						return Code(ExitFail)
					}
					return nil
				}
				select {
				case <-ctx.Done():
					fmt.Fprintln(out, "author watch: stopped")
					return nil
				case <-time.After(time.Duration(t.AuthorIntervalS) * time.Second):
				}
			}
		}}
	addTargetFlag(c)
	requireTarget(c)
	c.Flags().Bool("once", false, "one pass, then exit (0: nothing to do or a PR opened; 1: a draft failed)")
	c.Flags().Bool("redraft", false, "draft again, once per item and slice, even when this spec version was already drafted automatically (for example after a forge fix)")
	return c
}

func authorEnv(cmd *cobra.Command) (author.Env, string, error) {
	item, _ := cmd.Flags().GetString("item")
	l, err := layout()
	if err != nil {
		return author.Env{}, "", err
	}
	cfg, err := config.Load(l.Root, false, false)
	if err != nil {
		return author.Env{}, "", err
	}
	t, err := loadTarget(cmd, l, cfg)
	if err != nil {
		return author.Env{}, "", err
	}
	if t.Fixture {
		return author.Env{}, "", Exit(ExitError, "the test author works on a --target repository's items, not the fixture")
	}
	sc, err := hosts.Operator(t.Host())
	if err != nil {
		return author.Env{}, "", Exit(ExitError, "%v", err)
	}
	deps := readiness.Deps{Src: gate.ExecStatus{},
		Clone: func(repo, branch string) (string, string, error) {
			return fixture.FreshClone(t.Host(), repo, branch, 1)
		},
		OpenPRHeads: func(repo string) ([]string, error) {
			return hosts.OpenPilotHeads(context.Background(), sc, repo)
		}}
	deps.SkipHidden = true
	ready := func(t config.Target, item, sl string) (readiness.Result, error) {
		d := deps
		d.Slice = sl
		return readiness.Check(d, t, item, 0, "")
	}
	return author.Env{Target: t, EvidenceRoot: l.EvidenceRoot(), BuildDir: l.Build, Ready: ready,
		Identity: author.ResolveIdentity, OpenAuthorPRs: author.OpenAuthorPRs, Out: cmd.OutOrStdout()}, item, nil
}

// watchVerbosity is `author watch`'s diagnostics level: -vv unless -v or PILOT_VERBOSE says
// otherwise (then the level they chose, which PersistentPreRun already set).
func watchVerbosity(flagCount int, envSet bool) int {
	if flagCount == 0 && !envSet {
		return 2
	}
	return verbose.Level()
}

// authorWatchEnv is the drafting loop's environment (024): the pulled images, the author proxy,
// the author Job and its checks, and the target's roadmap. Step mode (021) uses it too.
func authorWatchEnv(e author.Env, p *pipeline.P) (author.WatchEnv, error) {
	imgs, err := images.Load(p.L) // the digests `./chalkeus forge up` pulled (as every run loads them)
	if err != nil {
		return author.WatchEnv{}, Exit(ExitError, "%v", err)
	}
	p.Imgs = imgs
	if why := p.Cfg.AuthorModelProblem(e.Target); why != "" { // 041 US1
		return author.WatchEnv{}, Exit(ExitError, "%s", why)
	}
	if !p.C.NSExists(cluster.AuthorProxyNS) {
		return author.WatchEnv{}, Exit(ExitError, "the author proxy %s is missing: run `./chalkeus forge up` first", cluster.AuthorProxyNS)
	}
	ck := checks.Deps{L: p.L, C: p.C, Out: io.Discard}
	je := author.JobEnv{Manifests: p.L.Manifests, Cluster: p.C, Runner: p.Runner, Images: p.Imgs,
		Model: p.Cfg.AuthorModel(e.Target), SpendCap: p.Cfg.Get("PILOT_SPEND_CAP_USD"), TokenCap: p.Cfg.Get("PILOT_TOKEN_CAP"),
		ModelFiles: p.Cfg.ModelFiles(), Deadline: images.AuthorDeadline(e.Target), FreeModels: e.Target.FreeModels == "on",
		Checks: func(ns, draftID string) []author.AuthorCheck {
			var out []author.AuthorCheck
			for _, r := range ck.RunAuthorChecks(ns, draftID, p.Imgs) {
				out = append(out, author.AuthorCheck{ID: r.ID, Result: r.Result, Detail: r.Detail})
			}
			return out
		}}
	var slices func(string, string) string
	if e.Target.SliceRuns == "on" { // 026: draft each item's current slice; off: whole items, as before
		slices = slice.CurrentOf
	}
	return author.WatchEnv{Env: e, Baseline: p.AuthorBaseline, Status: targetStatus(e.Target), Slices: slices,
		Job: func(ctx context.Context, d *author.Draft, attempt int, prompt string) author.JobRecord {
			return author.RunJob(ctx, je, d, attempt, prompt)
		}}, nil
}

// targetStatus is `spec status --json` of the target's branch, on a fresh clone.
func targetStatus(t config.Target) func() (string, error) {
	return func() (string, error) {
		dir, _, err := fixture.FreshClone(t.Host(), t.Repo, t.Branch, 1)
		if err != nil {
			return "", err
		}
		defer func() { _ = os.RemoveAll(dir) }()
		_, out := gate.ExecStatus{}.Status(dir)
		return out, nil
	}
}
