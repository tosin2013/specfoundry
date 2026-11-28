package config

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

// ModelProbe is the outcome of asking the worker's model provider whether its key is accepted.
type ModelProbe struct {
	Provider string
	Status   int    // HTTP status, 0 if the request failed
	Message  string // the provider's error message (never the key), clipped
}

// ProbeModel sends one tiny chat completion (max_tokens 1, a few tokens) with the worker's key
// and model, from this machine, to <baseURL>/chat/completions (OpenAI-compatible providers and
// gateways). A listing endpoint isn't enough: a gateway may list models for a key it then
// refuses to serve. It reads the key from the worker's key file and never returns or prints it.
func (c *Config) ProbeModel(ctx context.Context) (ModelProbe, error) { return c.ProbeModelAs(ctx, "") }

// ProbeModelAs is ProbeModel with another model of the same provider (041: the test author's);
// "" means the worker's configured model.
func (c *Config) ProbeModelAs(ctx context.Context, as string) (ModelProbe, error) {
	raw, err := os.ReadFile(filepath.Join(c.ModelDir, "opencode.json"))
	if err != nil {
		return ModelProbe{}, fmt.Errorf("no worker model config: run `./chalkeus forge import-opencode`")
	}
	var doc map[string]any
	if err := json.Unmarshal(raw, &doc); err != nil {
		return ModelProbe{}, err
	}
	model, _ := doc["model"].(string)
	prov, modelID, _ := strings.Cut(model, "/")
	if as != "" {
		ap, aid, _ := strings.Cut(as, "/")
		if ap != prov {
			return ModelProbe{Provider: ap}, fmt.Errorf("model %s is not on the worker's provider %s", as, prov)
		}
		modelID = aid
	}
	provs, _ := doc["providers"].(map[string]any)
	p, _ := provs[prov].(map[string]any)
	settings, _ := p["settings"].(map[string]any)
	base, _ := settings["baseURL"].(string)
	ref, _ := settings["apiKey"].(string)
	m := fileRefRE.FindStringSubmatch(ref)
	if base == "" || m == nil {
		return ModelProbe{Provider: prov}, fmt.Errorf("the worker's provider %s has no baseURL or key file reference", prov)
	}
	keyRaw, err := os.ReadFile(filepath.Join(c.ModelDir, filepath.Base(m[1])))
	if err != nil {
		return ModelProbe{Provider: prov}, fmt.Errorf("the worker's key file %s is missing", filepath.Base(m[1]))
	}
	key := strings.TrimSpace(string(keyRaw))
	ctx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()
	payload, _ := json.Marshal(map[string]any{"model": modelID, "max_tokens": 1,
		"messages": []map[string]string{{"role": "user", "content": "Reply with OK."}}})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimSuffix(base, "/")+"/chat/completions", strings.NewReader(string(payload)))
	if err != nil {
		return ModelProbe{Provider: prov}, err
	}
	req.Header.Set("Authorization", "Bearer "+key)
	req.Header.Set("Content-Type", "application/json")
	// Coding-agent gateways (OpenCode Go) refuse requests without a session id, and ask clients to
	// name themselves rather than send a generic HTTP library's user agent.
	req.Header.Set("User-Agent", "chalkeus-forge")
	req.Header.Set("X-Opencode-Session", fmt.Sprintf("chalkeus-doctor-%d", time.Now().UnixNano()))
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return ModelProbe{Provider: prov}, fmt.Errorf("could not reach the model provider: %v", strings.ReplaceAll(err.Error(), key, "[key]"))
	}
	defer func() { _ = resp.Body.Close() }()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
	out := ModelProbe{Provider: prov, Status: resp.StatusCode}
	if resp.StatusCode >= 300 {
		var e struct {
			Error   any    `json:"error"`
			Message string `json:"message"`
		}
		msg := ""
		if json.Unmarshal(body, &e) == nil {
			switch x := e.Error.(type) {
			case map[string]any:
				msg, _ = x["message"].(string)
			case string:
				msg = x
			}
			if msg == "" {
				msg = e.Message
			}
		}
		msg = RedactProviderMessage(msg, key)
		if len(msg) > 200 {
			msg = msg[:200]
		}
		out.Message = msg
	}
	return out, nil
}

// keyFragmentRE matches what providers echo about a key in their errors: a masked key
// (`sk-...jTCQ`) or a key hash (64 hex digits).
var keyFragmentRE = regexp.MustCompile(`\bsk-[^\s,;"']*|\b[0-9a-fA-F]{64}\b`)

// RedactProviderMessage removes the key and anything a provider echoes about it.
func RedactProviderMessage(msg, key string) string {
	if key != "" {
		msg = strings.ReplaceAll(msg, key, "[key]")
	}
	return keyFragmentRE.ReplaceAllString(msg, "[key]")
}
