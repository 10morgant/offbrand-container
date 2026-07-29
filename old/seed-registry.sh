#!/usr/bin/env bash

set -euo pipefail

REGISTRY="${REGISTRY:-localhost:5000}"
NAMESPACE="${NAMESPACE:-a}"
COPIES_PER_SOURCE="${COPIES_PER_SOURCE:-2}"
VERSIONS_PER_REPO="${VERSIONS_PER_REPO:-10}"

SOURCES=(
  "hello-world:latest"
  "registry:2"
  "registry:2.8.3"
  "alpine:3.17"
  "alpine:3.18"
  "alpine:3.19"
  "alpine:3.20"
  "alpine:3.21"
  "alpine:3.22"
  "alpine:latest"
  "busybox:1.35"
  "busybox:1.36"
  "busybox:1.37"
  "busybox:latest"
)

sanitize_name() {
  local image_ref="$1"

  image_ref="${image_ref//\//-}"
  image_ref="${image_ref//:/-}"
  printf '%s' "$image_ref"
}

main() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker CLI not found in PATH" >&2
    exit 1
  fi

  if [[ ! "$COPIES_PER_SOURCE" =~ ^[0-9]+$ ]] || [[ "$COPIES_PER_SOURCE" -lt 1 ]]; then
    echo "COPIES_PER_SOURCE must be a positive integer" >&2
    exit 1
  fi

  if [[ ! "$VERSIONS_PER_REPO" =~ ^[0-9]+$ ]] || [[ "$VERSIONS_PER_REPO" -lt 10 ]] || [[ "$VERSIONS_PER_REPO" -gt 50 ]]; then
    echo "VERSIONS_PER_REPO must be an integer between 10 and 50" >&2
    exit 1
  fi

  local total_sources="${#SOURCES[@]}"
  local total_repos=$(( total_sources * COPIES_PER_SOURCE ))
  local total_pushes=$(( total_repos * VERSIONS_PER_REPO ))

  echo "Registry: $REGISTRY"
  echo "Namespace: $NAMESPACE"
  echo "Sources: $total_sources"
  echo "Target repos to create: $total_repos"
  echo "Versions per repo: $VERSIONS_PER_REPO"
  echo "Total tagged images to push: $total_pushes"
  echo
  echo "Note: if your registry is plain HTTP, Docker must trust it as an insecure registry."
  echo

  local source
  local copy_index
  local version_index
  local version_tag
  local target_repo
  local target_ref

  for source in "${SOURCES[@]}"; do
    echo "Pulling $source"
    docker pull "$source"

    for ((copy_index = 1; copy_index <= COPIES_PER_SOURCE; copy_index++)); do
      target_repo="$REGISTRY/$NAMESPACE/$(sanitize_name "$source")-$copy_index"

      for ((version_index = 1; version_index <= VERSIONS_PER_REPO; version_index++)); do
        version_tag=$(printf 'v%02d' "$version_index")
        target_ref="$target_repo:$version_tag"

        echo "Pushing $target_ref"
        docker tag "$source" "$target_ref"
        docker push "$target_ref"
      done
    done
  done

  echo
  echo "Done. Pushed $total_pushes tagged images across $total_repos repos to $REGISTRY/$NAMESPACE/."
}

main "$@"