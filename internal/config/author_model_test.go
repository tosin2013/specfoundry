package config

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestAuthorModel(t *testing.T) {
	c := &Config{Values: map[string]string{"PILOT_MODEL": "opencode-go/beam-free"}}
	if got := c.AuthorModel(Target{}); got != "opencode-go/beam-free" {
		t.Fatalf("no setting: %q, want the worker's model", got)
	}
	if why := c.AuthorModelProblem(Target{}); why != "" {
		t.Fatalf("same model: %q", why)
	}
	c.Values["PILOT_AUTHOR_MODEL"] = "opencode-go/strong"
	if got := c.AuthorModel(Target{}); got != "opencode-go/strong" {
		t.Fatalf("forge.env: %q", got)
	}
	tg := Target{AuthorModel: "opencode-go/stronger"}
	if got := c.AuthorModel(tg); got != "opencode-go/stronger" {
		t.Fatalf("target profile wins: %q", got)
	}
	if why := c.AuthorModelProblem(tg); why != "" {
		t.Fatalf("same provider: %q", why)
	}
	// A paid author beside a free worker on the same provider is allowed: the free-model opt-in
	// only governs free models, never a paid one (041 US1).
	if why := c.AuthorModelProblem(Target{AuthorModel: "opencode-go/deepseek-v4-pro"}); why != "" {
		t.Fatalf("paid author, free worker: %q", why)
	}
	if why := c.AuthorModelProblem(Target{AuthorModel: "openai/gpt"}); !strings.Contains(why, "provider openai") || !strings.Contains(why, "opencode-go") {
		t.Fatalf("other provider: %q", why)
	}
}

func TestAuthorModelFromProfile(t *testing.T) {
	c := targetCfg(t)
	writeTarget(t, c, "greeting", goodTarget+"FORGE_AUTHOR_MODEL= opencode-go/strong \n")
	tg, err := c.LoadTarget("greeting", "")
	if err != nil {
		t.Fatal(err)
	}
	if tg.AuthorModel != "opencode-go/strong" {
		t.Fatalf("AuthorModel %q", tg.AuthorModel)
	}
}

func TestProbeModelAs(t *testing.T) {
	var model string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		model, _ = body["model"].(string)
		_, _ = w.Write([]byte(`{"choices":[{"message":{"content":"OK"}}]}`))
	}))
	defer srv.Close()
	c := probeCfg(t, srv.URL)
	if p, err := c.ProbeModelAs(context.Background(), "gw/strong"); err != nil || p.Status != 200 || model != "strong" {
		t.Fatalf("%+v %v model=%q", p, err, model)
	}
	if _, err := c.ProbeModelAs(context.Background(), "other/x"); err == nil || !strings.Contains(err.Error(), "not on the worker's provider gw") {
		t.Fatalf("other provider: %v", err)
	}
}
