package cli

import (
	"context"
	"fmt"

	"github.com/tosin2013/chalkeus/internal/config"
	"github.com/tosin2013/chalkeus/internal/doctor"
)

// doctorAuthorModel reports the test author's model (041 US1): which model drafts hidden tests,
// that it shares the worker's provider, and that the provider accepts the key for it.
func doctorAuthorModel(ctx context.Context, r *doctor.Report, cfg *config.Config, t config.Target) {
	am, wm := cfg.AuthorModel(t), cfg.Get("PILOT_MODEL")
	if am == wm {
		r.Add("cluster", "author model", doctor.Info, fmt.Sprintf("drafts use the worker's model %s (set FORGE_AUTHOR_MODEL to draft hidden tests with a stronger one)", wm))
		return
	}
	if why := cfg.AuthorModelProblem(t); why != "" {
		r.Add("cluster", "author model", doctor.Fail, why)
		return
	}
	probe, err := cfg.ProbeModelAs(ctx, am)
	switch {
	case err != nil:
		r.Add("cluster", "author model", doctor.Fail, fmt.Sprintf("%s: %v", am, err))
	case probe.Status >= 200 && probe.Status < 300:
		r.Add("cluster", "author model", doctor.Pass, fmt.Sprintf("%s drafts hidden tests (worker: %s); the provider accepts the key for it", am, wm))
	case probe.Status == 401 || probe.Status == 403 || probe.Status == 404:
		r.Add("cluster", "author model", doctor.Fail, fmt.Sprintf("the provider refused %s (%d): %s", am, probe.Status, probe.Message))
	default:
		r.Add("cluster", "author model", doctor.Warn, fmt.Sprintf("couldn't confirm %s: the provider answered %d to a one-token test request", am, probe.Status))
	}
}
