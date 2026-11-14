"""`pilot` command line (contracts/cli.md)."""
from __future__ import annotations

import argparse
import json
import sys
import traceback

from . import paths
from .config import ConfigError

EXIT_OK, EXIT_FAIL, EXIT_ERROR, EXIT_GUARD = 0, 1, 2, 3
EXIT_AWAIT_MERGE, EXIT_DECLINED, EXIT_AWAIT_RETRY, EXIT_REFUSE = 4, 5, 6, 10


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pilot", description="specfoundry M1 pilot")
    sub = p.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("up", help="stand up kind + Calico, registry, images, proxies, publisher")
    up.add_argument("--cluster-only", action="store_true", help="only kind + Calico (no config needed)")
    up.add_argument("--local-build", action="store_true",
                    help="build images locally into a kind-local registry instead of pulling pinned digests")
    pt = sub.add_parser("publisher-token", help="write publisher.env from a hidden prompt and verify its scope")
    pt.add_argument("--check-only", action="store_true", help="only verify the existing publisher.env")
    io = sub.add_parser("import-opencode", help="reuse your existing OpenCode config (provider + key file) for the worker")
    io.add_argument("--from", dest="src", default="~/.config/opencode", help="OpenCode config dir (default ~/.config/opencode)")
    io.add_argument("--model", help="<provider>/<model> to use (default: the config's \"model\")")
    io.add_argument("--fixture-repo", help="owner/name of your -pilot-fixture repo, written to a new pilot.env")
    io.add_argument("--force", action="store_true", help="replace an existing worker OpenCode config")
    rf = sub.add_parser("reset-fixture", help="force-reset the throwaway fixture repo")
    rf.add_argument("--yes", action="store_true")
    sub.add_parser("run", help="start a new pilot run")
    rs = sub.add_parser("resume", help="resume a paused run")
    rs.add_argument("--run")
    g = sub.add_parser("gate", help="evaluate the gate for one task")
    g.add_argument("task", choices=["A", "B"])
    g.add_argument("--root", help="evaluate this directory instead of a fresh clone")
    a = sub.add_parser("audit", help="evidence-only audit")
    a.add_argument("--run")
    sub.add_parser("down", help="tear down and verify")
    s = sub.add_parser("status", help="print run state")
    s.add_argument("--run")
    return p


def cmd_status(args) -> int:
    from . import evidence
    run = evidence.load_run(args.run)
    if not run:
        print("no runs")
        return EXIT_OK
    print(json.dumps(run.state, indent=2, sort_keys=True))
    return EXIT_OK


def cmd_gate(args) -> int:
    from . import evidence, gate
    run = evidence.active_run()
    seq = run.next_gate_seq() if run else 0
    if args.root:
        decision = gate.evaluate(args.task, paths.TASKS[args.task], args.root, seq=seq,
                                 out_dir=(run.dir / "gate") if run else None, repo="local:" + args.root)
    else:
        from . import config
        cfg = config.load(require_secrets=False)
        decision = gate.evaluate_fresh(cfg, args.task, seq=seq, out_dir=(run.dir / "gate") if run else None)
    if run:
        run.event("gate", args.task, None, f"gate_{decision['decision']}", ",".join(decision["reasons"]))
    print(json.dumps(decision, indent=2, sort_keys=True))
    return EXIT_OK if decision["decision"] == "allow" else EXIT_REFUSE


def require_up() -> None:
    if not paths.UP_OK.exists():
        raise ConfigError("`pilot up` has not completed (missing pilot/.build/up.ok)")


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.cmd == "status":
            return cmd_status(args)
        if args.cmd == "gate":
            return cmd_gate(args)
        if args.cmd == "down":
            from . import cluster
            return cluster.down()
        if args.cmd == "up":
            from . import cluster, config
            cfg = None if args.cluster_only else config.load()
            cluster.up(cfg, cluster_only=args.cluster_only, local_build=args.local_build)
            return EXIT_OK
        if args.cmd == "publisher-token":
            from . import config, publisher_token
            return publisher_token.run(config.load(require_secrets=False), check_only=args.check_only)
        if args.cmd == "import-opencode":
            from pathlib import Path
            from . import import_opencode
            return import_opencode.run(Path(args.src).expanduser(), model=args.model,
                                       fixture_repo=args.fixture_repo, force=args.force)
        if args.cmd == "reset-fixture":
            from . import config, fixture
            return fixture.reset(config.load(require_secrets=False), yes=args.yes)
        if args.cmd == "audit":
            from . import audit, evidence
            run = evidence.load_run(args.run)
            if not run:
                print("no run found", file=sys.stderr)
                return EXIT_ERROR
            ok = audit.run(run, final=True)
            return EXIT_OK if ok else EXIT_FAIL
        if args.cmd in ("run", "resume"):
            from . import config, pipeline
            require_up()
            cfg = config.load()
            return pipeline.run(cfg) if args.cmd == "run" else pipeline.resume(cfg, args.run)
    except ConfigError as e:
        print(f"pilot: {e}", file=sys.stderr)
        return e.code
    except KeyboardInterrupt:
        print("pilot: interrupted", file=sys.stderr)
        return EXIT_ERROR
    except NotImplementedError as e:
        print(f"pilot: not implemented: {e}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        print(f"pilot: error: {e}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_ERROR
