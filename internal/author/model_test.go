package author

import (
	"strings"
	"testing"
)

// 041 US1: the PR body names the model that drafted the tests; a hand-written draft has none.
func TestPRBodyNamesTheModel(t *testing.T) {
	d := &Draft{Repo: "o/r", Item: "004", Title: "zod 4", Level: "minimal", Identity: "me", CompanionDir: "documcp/items/004",
		Checks: []CheckRecord{{Result: CodeDraftOK, DraftHash: "abcdef0123456789"}}, BaseRevision: "0123456789abcdef"}
	if body := PRBody(d, nil, Map{}); strings.Contains(body, "Drafted by: ") {
		t.Fatalf("hand-written draft names a model:\n%s", body)
	}
	d.Model = "opencode-go/strong"
	if body := PRBody(d, nil, Map{}); !strings.Contains(body, "- Drafted by: `opencode-go/strong` (041).") {
		t.Fatalf("no model line:\n%s", body)
	}
}
