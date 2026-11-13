# Feature Specification: M2 hardened images and Kelos competitive review

**Feature Branch**: `003-m2-kelos-backend`

**Created**: 2026-11-13 (rescoped the same day: roadmap 1.4.0, constitution 1.1.0)

**Status**: Draft

**Roadmap**: `.specify/memory/roadmap.md` entry 003 (depends on 002, verified 2026-11-13)

**Input**: User description: "003" — roadmap entry 003, renamed from "M2 Kelos backend":
build the pilot's images in GitHub so they run on laptops and in enterprise environments,
and write a factual competitive review of Kelos.

## Context

The owner's target is **laptops** (kind) and **enterprise** environments (OpenShift
restricted SCC, arbitrary UID, mirrored or air-gapped registries, proxies, a small trust
base, audit evidence). The constitution (1.1.0, VI and VII) now records this.

Reading Kelos v0.64.0's source showed that it is a convenience-first agent runner:
- the agent holds a Git token and opens PRs itself;
- its bundled images use passwordless sudo;
- every Task Job retries once by itself;
- telemetry is on by default;
- images are pinned by tag;
- a cluster-wide controller can read every Secret.

That model is the opposite of specfoundry's least-privilege governance. Kelos is therefore
treated as a **competitor and design reference**, not a dependency (C-05).

003 delivers two things:
1. **Hardened, GitHub-built images**, used by every later milestone. They're built from
   verified upstream sources instead of an operator's local binary, published publicly, and
   pulled by digest (C-09).
2. **A competitive review** that compares Kelos and specfoundry factually against the
   security bar, and turns the Kelos features enterprises expect into candidate roadmap
   items.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pilot images built in GitHub and pulled by digest (Priority: P1)

As the owner, I can repeat the pilot on any machine without building images from my own
laptop's binaries. The worker, tools and egress-proxy images are built by GitHub from
verified upstream sources, published as public images, and pulled by digest. The CNI
manifest is checked against a pinned hash before it is applied.

**Why this priority**: C-09 and constitution VII. Every later milestone (004, 005, 006)
builds on these images.

**Independent Test**: A build in GitHub publishes the three images. A fresh `pilot up`
pulls them by the digests recorded in the repo, and a full plain-Jobs pilot run with those
images passes its audit. Changing a pinned digest or the CNI hash makes stand-up stop.

**Acceptance Scenarios**:

1. **Given** a change to an image's sources, **When** GitHub builds it, **Then** the image
   is published to the public registry and its digest is proposed for the repo's pins
   through a reviewable change, never a silent update.
2. **Given** the worker image build, **When** it fetches OpenCode, **Then** it uses an
   upstream release verified against its published checksum, never an operator's local
   binary. The image is non-root, without sudo, and contains no secrets.
3. **Given** `pilot up`, **When** images are needed, **Then** they are pulled by digest
   from the public registry. A local build happens only when the operator explicitly asks.
4. **Given** the CNI manifest is downloaded, **When** its hash does not match the pinned
   value, **Then** stand-up stops before applying it.
5. **Given** a pilot run on the GitHub-built images, **When** it completes, **Then** the
   audit passes in full, with the same checks as 002.

---

### User Story 2 - Images ready for enterprise clusters (Priority: P2)

As an enterprise operator, I can run the same images under a restricted policy: any
assigned user ID, no root, no sudo, a read-only root filesystem, and egress only through
proxies. I can also mirror them into my own registry without rebuilding them.

**Why this priority**: The enterprise half of the target (constitution VII). OpenShift
itself is 005, but the images should not need redoing then.

**Independent Test**: Run each image locally with an arbitrary non-default user ID and a
read-only root filesystem. The worker, grader and publisher entrypoints still work. Mirror
the images to another registry by digest, and a pilot run referencing the mirror works the
same.

**Acceptance Scenarios**:

1. **Given** an arbitrary user ID (not the image's default), **When** each image runs with
   a read-only root filesystem and its usual writable scratch mounts, **Then** it completes
   its job.
2. **Given** the images are copied by digest to another registry, **When** the pins point
   at that registry, **Then** the pilot behaves identically. The image build takes the
   registry as a parameter, so another registry (e.g. Quay for OpenShift, 005) can be added
   without redesign.
3. **Given** a corporate HTTP proxy is required, **When** the images run, **Then** the
   documented proxy settings are honoured, and no image needs direct internet access.

---

### User Story 3 - A factual Kelos competitive review (Priority: P2)

As the owner, I can read a short, factual comparison of Kelos (the pinned version) and
specfoundry against the security bar, plus a list of Kelos capabilities that enterprises
are likely to expect. That tells me what to emphasise and what to add to the roadmap.

**Why this priority**: Positioning (constitution VI) and roadmap input. It changes no code.

**Independent Test**: The review exists in the repo, scores both products on SB-1–SB-8
with citations, and lists gap items. Each gap item is either proposed as a roadmap entry or
noted, so it doesn't get lost.

**Acceptance Scenarios**:

1. **Given** Kelos v0.64.0 and specfoundry at the current commit, **When** the review is
   written, **Then** each security-bar item SB-1–SB-8 is described for both, with a
   citation (source path or doc section at the pinned version, a hands-on probe, or our own
   evidence).
2. **Given** the review, **When** it lists Kelos capabilities, **Then** each one is marked
   *have*, *gap* or *won't do*. Each *gap* names the governance or security constraint our
   version would have to keep.
3. **Given** the review is intended to be public, **When** it describes Kelos, **Then** it
   states facts and versions, makes no disparaging claims, and copies no Kelos code. Ideas
   borrowed from Kelos are attributed.
4. **Given** the review's gap list, **When** it is accepted, **Then** the owner can add
   entries to the roadmap via `/speckit-roadmap-write` (not part of this spec's work).

---

### Edge Cases

- The upstream OpenCode release has no published checksum, or it doesn't match: the image
  build fails; it never falls back to an unverified download.
- The upstream OpenCode binary differs from the one used in 002: a fresh plain-Jobs pilot
  run (US1 scenario 5) re-validates the grading and induction results.
- The public registry is unreachable during `pilot up`: stand-up stops with the reason; it
  does not silently switch to a local build.
- A digest PR from the image build is not merged: `pilot up` keeps using the previously
  pinned digests.
- An image works only as its default user ID: US2 fails until it is fixed.
- A Kelos fact cannot be confirmed from source or a probe: the review marks it "unverified"
  rather than guessing.

## Requirements *(mandatory)*

### Functional Requirements

**Images built in GitHub (C-09)**

- **FR-001**: The worker, tools and egress-proxy images MUST be built by GitHub (not on an
  operator's machine), from sources in this repository plus verified upstream inputs.
- **FR-002**: The worker's OpenCode MUST come from an upstream release checked against its
  published checksum. The tools image's spec-status binary MUST be checked against a
  pinned checksum.
- **FR-003**: The images MUST be published to a public registry (GHCR for kind and local
  runs), contain no secrets, and run non-root without sudo.
- **FR-004**: New image digests MUST reach the repository's pins only through a reviewable
  change. The build MUST NOT push to the default branch.
- **FR-005**: `pilot up` MUST pull images by the pinned digests by default, MUST refuse
  tag-only or missing references, and MUST build locally only when the operator explicitly
  asks. Which source was used MUST be recorded in the evidence.
- **FR-006**: The registry MUST be a parameter of the image build.
- **FR-007**: The CNI manifest MUST be checked against a pinned hash before it is applied;
  a mismatch stops stand-up.

**Enterprise readiness**

- **FR-008**: Every image MUST work under an arbitrary user ID, with a read-only root
  filesystem and only declared writable mounts.
- **FR-009**: The images MUST honour standard HTTP proxy settings, and MUST NOT require
  direct internet access at run time (C-07).
- **FR-010**: The worker image SHOULD also provide a Kelos-compatible entrypoint, so teams
  that already run Kelos can use the hardened image. This adds no dependency on Kelos.

**Competitive review (C-05)**

- **FR-011**: A written review MUST compare Kelos (one pinned version) and specfoundry on
  SB-1–SB-8, each with a citation or "unverified":
  - **SB-1**: no SCM credential in the worker.
  - **SB-2**: own image, non-root, no sudo, pinned by digest.
  - **SB-3**: no automatic retry.
  - **SB-4**: no phone-home telemetry; operator observability only (C-10).
  - **SB-5**: every image pinned by digest.
  - **SB-6**: isolation, C-07 and C-08.
  - **SB-7**: service-account token off.
  - **SB-8**: platform-component privileges.
- **FR-012**: The review MUST list Kelos capabilities relevant to enterprises (e.g. harness
  coverage, triggers, sessions, console, spend budgets, install experience), each marked
  *have*, *gap* or *won't do*, with the constraint any implementation must keep.
- **FR-013**: The review MUST be factual and publishable: versions stated, no disparaging
  claims, no copied Kelos code; borrowed ideas attributed.
- **FR-014**: 003 MUST NOT install, adapt or fork Kelos (C-05). Hands-on probes for the
  review run on a throwaway cluster and are torn down.

### Key Entities

- **Pilot image set**: the worker, tools and egress images built by GitHub, with their
  public registry, digests, and the upstream inputs (and checksums) they were built from.
- **Pinned dependency set**: the image digests and the CNI manifest hash used by a run.
- **Competitive review**: SB-1–SB-8 for both products with citations, the capability gap
  list, and probe records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of a pilot run's images are pulled by digest from the public registry,
  and 0 are built from an operator's local binary.
- **SC-002**: A plain-Jobs pilot run on the GitHub-built images passes 100% of its audit
  (the same AU checks as 002) and 100% of the live isolation checks.
- **SC-003**: Each of the three images runs to completion under an arbitrary user ID with a
  read-only root filesystem (3 of 3).
- **SC-004**: A changed CNI hash or a tag-only image reference stops stand-up 100% of the
  time.
- **SC-005**: New digests reach the pins only through merged pull requests: 0 direct pushes
  by the build.
- **SC-006**: The review covers 8 of 8 security-bar items for both products, with a
  citation or "unverified", and lists at least 5 capability items, each marked
  have/gap/won't do.
- **SC-007**: 0 Kelos components are installed in the pilot's clusters, and 0 lines of Kelos
  code are copied.

## Assumptions

- Owner decisions (2026-11-13): security first; Kelos is a competitor and reference, not a
  dependency; target laptops and enterprise; telemetry means operator observability only;
  images are public GHCR packages while the source repo stays private (it may go public
  later).
- Upstream OpenCode is `anomalyco/opencode` v2.2.7 (`opencode-linux-x64.tar.gz` with a
  `SHA256SUMS` file on the release).
- The pilot fixture, hidden grading tests, throwaway GitHub repo, publisher token and
  operator OpenCode configuration from 002 are reused for the validation run.
- OpenShift itself, Quay publishing and UBI variants are 005. Operator observability (C-10)
  is planned separately (roadmap Q6).
- The review document lives in this spec folder as `kelos-review.md`.
