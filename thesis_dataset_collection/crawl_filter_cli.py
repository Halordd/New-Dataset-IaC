#!/usr/bin/env python3
"""Terraform GitHub crawl and filter pipeline (fully runnable).

This CLI implements the 5-layer filtering flow:
1) Repository search
2) Maturity filtering
3) Syntax validation (terraform init/validate)
4) Structural filtering
5) Behavior-based filtering
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import os
import shutil
import statistics
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


LOG = logging.getLogger("crawl_filter")


@dataclass
class Thresholds:
    min_stars: int = 10
    min_forks: int = 5
    max_age_months: int = 24
    outlier_threshold: float = 3.0


@dataclass
class RepoMetadata:
    repo_id: int
    full_name: str
    html_url: str
    stars: int
    forks: int
    months_since_last_commit: int
    has_readme: bool
    default_branch: str = "main"
    head_sha: str = "0" * 40
    license: Optional[str] = None
    readme_text: str = ""


@dataclass
class TerraformFile:
    path: str
    sha256: str
    content: str


@dataclass
class Candidate:
    repo: RepoMetadata
    terraform_files: List[TerraformFile] = field(default_factory=list)
    feature_vector: Dict[str, float] = field(default_factory=dict)
    behavior_outlier_score: float = 0.0
    keyword_exclusion_pass: bool = True
    maturity_pass: bool = False
    syntax_pass: bool = False
    structural_pass: bool = False
    behavior_pass: bool = False
    accepted: bool = False
    reject_reason: Optional[str] = None


class GitHubClient:
    def __init__(self, token: Optional[str], request_timeout: int = 30) -> None:
        self.token = token
        self.request_timeout = request_timeout
        self.base_url = "https://api.github.com"

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "terraform-dataset-crawler",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"
        req = Request(url=url, headers=self._headers(), method="GET")
        try:
            with urlopen(req, timeout=self.request_timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except HTTPError as exc:
            if exc.code == 403:
                reset = exc.headers.get("X-RateLimit-Reset")
                if reset and reset.isdigit():
                    wait_seconds = max(0, int(reset) - int(time.time()))
                    raise RuntimeError(
                        f"GitHub API rate limit exceeded. Retry after {wait_seconds}s."
                    ) from exc
            if exc.code == 404:
                return None
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"GitHub API error {exc.code} at {url}: {detail}") from exc

    def search_repositories(self, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        query_keywords = keywords + ["language:HCL"]
        query = " ".join(query_keywords)
        items: List[Dict[str, Any]] = []
        page = 1
        while len(items) < limit:
            per_page = min(100, limit - len(items))
            result = self._request_json(
                "/search/repositories",
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
            )
            page_items = result.get("items", []) if isinstance(result, dict) else []
            if not page_items:
                break
            items.extend(page_items)
            page += 1
        return items[:limit]

    def get_default_branch_head_sha(self, full_name: str, default_branch: str) -> Optional[str]:
        result = self._request_json(f"/repos/{full_name}/commits/{default_branch}")
        if not isinstance(result, dict):
            return None
        return result.get("sha")

    def get_readme_text(self, full_name: str) -> Optional[str]:
        result = self._request_json(f"/repos/{full_name}/readme")
        if not isinstance(result, dict):
            return None
        encoded = result.get("content")
        if not encoded:
            return ""
        raw = base64.b64decode(encoded)
        return raw.decode("utf-8", errors="ignore")

    def get_tree(self, full_name: str, ref_sha: str) -> Optional[Dict[str, Any]]:
        result = self._request_json(f"/repos/{full_name}/git/trees/{ref_sha}", params={"recursive": 1})
        if isinstance(result, dict):
            return result
        return None

    def get_blob_text_and_sha256(self, full_name: str, blob_sha: str) -> Optional[TerraformFile]:
        result = self._request_json(f"/repos/{full_name}/git/blobs/{blob_sha}")
        if not isinstance(result, dict):
            return None
        encoded = result.get("content")
        if not encoded:
            return None
        content_bytes = base64.b64decode(encoded)
        tf_sha = hashlib.sha256(content_bytes).hexdigest()
        text = content_bytes.decode("utf-8", errors="ignore")
        # Path is filled by caller.
        return TerraformFile(path="", sha256=tf_sha, content=text)


def _months_since(iso_timestamp: str) -> int:
    parsed = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    days = max(0, (now - parsed).days)
    return days // 30


def search_github_repositories(
    client: GitHubClient,
    keywords: List[str],
    limit: int,
) -> List[RepoMetadata]:
    LOG.info("Search query keywords: %s", keywords)
    raw_items = client.search_repositories(keywords, limit)
    repos: List[RepoMetadata] = []

    for item in raw_items:
        full_name = item["full_name"]
        default_branch = item.get("default_branch", "main")
        head_sha = client.get_default_branch_head_sha(full_name, default_branch)
        if not head_sha:
            continue

        readme_text = client.get_readme_text(full_name)
        has_readme = readme_text is not None
        repos.append(
            RepoMetadata(
                repo_id=item["id"],
                full_name=full_name,
                html_url=item["html_url"],
                stars=item.get("stargazers_count", 0),
                forks=item.get("forks_count", 0),
                months_since_last_commit=_months_since(item["pushed_at"]),
                has_readme=has_readme,
                default_branch=default_branch,
                head_sha=head_sha,
                license=(item.get("license") or {}).get("spdx_id"),
                readme_text=readme_text or "",
            )
        )
    return repos


def keyword_exclusion(repo: RepoMetadata, forbidden_keywords: List[str]) -> bool:
    haystack = f"{repo.full_name}\n{repo.readme_text}".lower()
    return any(word.lower() in haystack for word in forbidden_keywords)


def repo_meets_maturity(repo: RepoMetadata, th: Thresholds) -> bool:
    if repo.stars < th.min_stars:
        return False
    if repo.forks < th.min_forks:
        return False
    if repo.months_since_last_commit > th.max_age_months:
        return False
    if not repo.has_readme:
        return False
    return True


def extract_tf_files(
    client: GitHubClient,
    repo: RepoMetadata,
    max_tf_files: int,
) -> List[TerraformFile]:
    tree = client.get_tree(repo.full_name, repo.head_sha)
    if not tree:
        return []
    if tree.get("truncated"):
        LOG.warning("Skipping %s because recursive tree is truncated.", repo.full_name)
        return []

    tf_entries = []
    for entry in tree.get("tree", []):
        if entry.get("type") != "blob":
            continue
        path = entry.get("path", "")
        if not path.endswith(".tf"):
            continue
        tf_entries.append(entry)
        if len(tf_entries) >= max_tf_files:
            break

    tf_files: List[TerraformFile] = []
    for entry in tf_entries:
        blob = client.get_blob_text_and_sha256(repo.full_name, entry["sha"])
        if not blob:
            continue
        blob.path = entry["path"]
        tf_files.append(blob)
    return tf_files


def _run_cmd(cmd: List[str], cwd: Path, timeout_sec: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )


def validate_terraform(
    tf_files: List[TerraformFile],
    terraform_bin: str,
    timeout_sec: int,
) -> bool:
    if not tf_files:
        return False

    with tempfile.TemporaryDirectory(prefix="tf-validate-") as tmp:
        root = Path(tmp)
        for tf in tf_files:
            target = root / tf.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(tf.content, encoding="utf-8")

        init_result = _run_cmd(
            [terraform_bin, "init", "-backend=false", "-get=false", "-no-color"],
            cwd=root,
            timeout_sec=timeout_sec,
        )
        if init_result.returncode != 0:
            LOG.debug("terraform init failed: %s", init_result.stderr.strip())
            return False

        validate_result = _run_cmd(
            [terraform_bin, "validate", "-no-color"],
            cwd=root,
            timeout_sec=timeout_sec,
        )
        if validate_result.returncode != 0:
            LOG.debug("terraform validate failed: %s", validate_result.stderr.strip())
            return False

    return True


def structural_check(tf_files: List[TerraformFile]) -> bool:
    resource_count = 0
    contains_aws = False
    for tf in tf_files:
        txt = tf.content
        resource_count += txt.count('resource "')
        if "aws_" in txt:
            contains_aws = True
    return resource_count >= 2 and contains_aws


def extract_features(tf_files: List[TerraformFile]) -> Dict[str, float]:
    joined = "\n".join(tf.content for tf in tf_files)
    return {
        "num_files": float(len(tf_files)),
        "num_resources": float(joined.count('resource "')),
        "num_modules": float(joined.count('module "')),
        "num_variables": float(joined.count('variable "')),
        "num_outputs": float(joined.count('output "')),
        "num_data_blocks": float(joined.count('data "')),
        "aws_token_count": float(joined.count("aws_")),
    }


def estimate_reference_distribution(
    vectors: List[Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    if not vectors:
        return {}
    keys = sorted(vectors[0].keys())
    dist: Dict[str, Dict[str, float]] = {}
    for key in keys:
        values = [v[key] for v in vectors]
        mean = statistics.mean(values)
        stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
        dist[key] = {"mean": mean, "stdev": stdev}
    return dist


def anomaly_score(vector: Dict[str, float], dist: Dict[str, Dict[str, float]]) -> float:
    if not dist:
        return 0.0
    z_sum = 0.0
    count = 0
    for key, value in vector.items():
        if key not in dist:
            continue
        mu = dist[key]["mean"]
        sigma = dist[key]["stdev"]
        z = 0.0 if sigma == 0 else abs((value - mu) / sigma)
        z_sum += z
        count += 1
    return z_sum / count if count else 0.0


def to_output_record(candidate: Candidate) -> Dict[str, object]:
    timestamp = datetime.now(timezone.utc).isoformat()
    terraform_files = [{"path": tf.path, "sha256": tf.sha256} for tf in candidate.terraform_files]

    return {
        "sample_id": f"{candidate.repo.repo_id}:{candidate.repo.head_sha[:12]}",
        "repo_id": candidate.repo.repo_id,
        "repo_full_name": candidate.repo.full_name,
        "repo_url": candidate.repo.html_url,
        "commit_sha": candidate.repo.head_sha,
        "crawl_timestamp": timestamp,
        "source": "github",
        "license": candidate.repo.license,
        "terraform_files": terraform_files,
        "feature_vector": candidate.feature_vector,
        "filter_trace": {
            "keyword_exclusion": not candidate.keyword_exclusion_pass,
            "maturity_pass": candidate.maturity_pass,
            "syntax_pass": candidate.syntax_pass,
            "structural_pass": candidate.structural_pass,
            "behavior_outlier_score": candidate.behavior_outlier_score,
            "behavior_pass": candidate.behavior_pass,
            "accepted": candidate.accepted,
            "reject_reason": candidate.reject_reason,
        },
    }


def collect_terraform_dataset(
    client: GitHubClient,
    keywords: List[str],
    thresholds: Thresholds,
    forbidden_keywords: List[str],
    search_limit: int,
    terraform_bin: str,
    terraform_timeout_sec: int,
    max_tf_files: int,
    dry_run: bool,
) -> List[Candidate]:
    repos = search_github_repositories(client, keywords, search_limit)
    provisional: List[Candidate] = []

    for repo in repos:
        cand = Candidate(repo=repo)
        if keyword_exclusion(repo, forbidden_keywords):
            cand.keyword_exclusion_pass = False
            cand.reject_reason = "keyword_exclusion"
            continue
        cand.keyword_exclusion_pass = True

        if not repo_meets_maturity(repo, thresholds):
            cand.maturity_pass = False
            cand.reject_reason = "maturity_failed"
            continue
        cand.maturity_pass = True

        tf_files = extract_tf_files(client, repo, max_tf_files=max_tf_files)
        if not tf_files:
            cand.reject_reason = "no_tf_files"
            continue
        if dry_run:
            cand.syntax_pass = True
        else:
            if not validate_terraform(tf_files, terraform_bin=terraform_bin, timeout_sec=terraform_timeout_sec):
                cand.syntax_pass = False
                cand.reject_reason = "terraform_validate_failed"
                continue
            cand.syntax_pass = True

        if not structural_check(tf_files):
            cand.structural_pass = False
            cand.reject_reason = "structural_failed"
            continue
        cand.structural_pass = True

        features = extract_features(tf_files)
        cand.terraform_files = tf_files
        cand.feature_vector = features
        provisional.append(cand)

    ref_dist = estimate_reference_distribution([c.feature_vector for c in provisional])
    accepted: List[Candidate] = []
    for cand in provisional:
        score = anomaly_score(cand.feature_vector, ref_dist)
        cand.behavior_outlier_score = score
        if score <= thresholds.outlier_threshold:
            cand.behavior_pass = True
            cand.accepted = True
            accepted.append(cand)
        else:
            cand.behavior_pass = False
            cand.accepted = False
            cand.reject_reason = "behavior_outlier"
    return accepted


def write_ndjson(records: Iterable[Dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Crawl and filter Terraform projects from GitHub.")
    p.add_argument("--keywords", nargs="+", required=True, help="Search keywords.")
    p.add_argument("--search-limit", type=int, default=100, help="Max repositories to inspect.")
    p.add_argument("--github-token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token.")
    p.add_argument("--min-stars", type=int, default=10)
    p.add_argument("--min-forks", type=int, default=5)
    p.add_argument("--max-age-months", type=int, default=24)
    p.add_argument("--outlier-threshold", type=float, default=3.0)
    p.add_argument("--max-tf-files", type=int, default=200, help="Max .tf files per repository.")
    p.add_argument(
        "--terraform-bin",
        default="terraform",
        help="Terraform executable path (default: terraform in PATH).",
    )
    p.add_argument(
        "--terraform-timeout-sec",
        type=int,
        default=120,
        help="Timeout for each terraform command execution.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip terraform init/validate for faster debugging.",
    )
    p.add_argument(
        "--forbidden-keywords",
        nargs="+",
        default=["demo", "lab", "test", "vulnerable", "insecure"],
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("output/terraform_dataset.ndjson"),
        help="Path to accepted dataset in NDJSON format.",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    thresholds = Thresholds(
        min_stars=args.min_stars,
        min_forks=args.min_forks,
        max_age_months=args.max_age_months,
        outlier_threshold=args.outlier_threshold,
    )

    if not args.dry_run and shutil.which(args.terraform_bin) is None:
        raise RuntimeError(
            f"Terraform binary not found: {args.terraform_bin}. "
            "Install Terraform or pass --terraform-bin with a valid path."
        )
    if args.dry_run:
        LOG.warning("Running in dry-run mode: terraform init/validate is skipped.")

    client = GitHubClient(token=args.github_token)

    accepted = collect_terraform_dataset(
        client=client,
        keywords=args.keywords,
        thresholds=thresholds,
        forbidden_keywords=args.forbidden_keywords,
        search_limit=args.search_limit,
        terraform_bin=args.terraform_bin,
        terraform_timeout_sec=args.terraform_timeout_sec,
        max_tf_files=args.max_tf_files,
        dry_run=args.dry_run,
    )
    records = [to_output_record(c) for c in accepted]
    write_ndjson(records, args.output)

    LOG.info("Accepted samples: %d", len(records))
    LOG.info("Output written to: %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
