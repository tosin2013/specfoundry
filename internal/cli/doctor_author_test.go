package cli

import (
	"context"
	"strings"
	"testing"

	"github.com/tosin2013/chalkeus/internal/config"
	"github.com/tosin2013/chalkeus/internal/doctor"
)

// 041 US1: doctor's author-model row without a network call: information while drafts use the
// worker's model, a failure for a model from another provider.
func TestDoctorAuthorModel(t *testing.T) {
	cfg := &config.Config{Values: map[string]string{"PILOT_MODEL": "opencode-go/beam-free"}}
	var r doctor.Report
	doctorAuthorModel(context.Background(), &r, cfg, config.Target{})
	if len(r.Rows) != 1 || r.Rows[0].Status != doctor.Info || !strings.Contains(r.Rows[0].Detail, "worker's model opencode-go/beam-free") {
		t.Fatalf("%+v", r.Rows)
	}
	r = doctor.Report{}
	doctorAuthorModel(context.Background(), &r, cfg, config.Target{AuthorModel: "openai/gpt"})
	if len(r.Rows) != 1 || r.Rows[0].Status != doctor.Fail || !strings.Contains(r.Rows[0].Detail, "provider openai") {
		t.Fatalf("%+v", r.Rows)
	}
}
