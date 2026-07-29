#!/usr/bin/env python3
"""
Generate random Docker namespaces/names/versions and push them to a local
registry (default: localhost:5000).

Requires: Docker installed and running, and a local registry container up, e.g.:
    docker run -d -p 5000:5000 --name registry registry:2

Usage:
    python3 generate_and_push_images.py
"""

import random
import string
import subprocess
import sys
import tempfile
import os

# ----------------------------------------------------------------------------
# CONFIG - control quantities and behavior here
# ----------------------------------------------------------------------------
REGISTRY = "localhost:5000"     # target registry
NUM_NAMESPACES = 50               # how many random namespaces (e.g. "acme")
NUM_NAMES_PER_NAMESPACE = 10       # how many random image names per namespace
NUM_VERSIONS_PER_NAME = 15         # how many random tags/versions per image name

BASE_IMAGE = "alpine:latest"     # small base image used to build from
UNIQUE_CONTENT = False             # if True, bake a random file into each image
# so every push is a genuinely distinct image
# (slower - does a docker build per image)
CLEANUP_LOCAL_IMAGES = True       # remove local tags after pushing, to save disk

# Word pools used to build readable-ish random names
ADJECTIVES = [
     "vivid", "curious", "fierce", "hollow", "bright",
    "clumsy", "eager", "frigid", "gloomy", "humble", "jagged", "lively", "muddy",
    "nimble", "obscure", "playful", "quaint", "rigid", "somber", "tender", "urgent",
    "vast", "wary", "zealous", "ancient", "bitter", "crisp", "dizzy", "elegant",
    "fragile", "graceful", "harsh", "immense", "jolly", "keen", "lush", "mellow",
    "noble", "odd", "pale", "quirky", "restless", "shy", "tidy", "unruly",
    "witty", "youthful"
]
NOUNS = [
    "prairie", "citadel", "vessel", "thistle", "corridor", "outpost", "sapling",
    "clover", "reservoir", "avenue",
    "mountain", "river", "shadow", "engine", "garden", "compass", "lantern", 
    "whisper", "canyon", "thunder", "pillow", "anchor",  "castle",
    "mirror", "puzzle", "voyage", "orchard", "tunnel", "glacier",
    "feather", "kettle", "chapter", "island", "velvet", "bridge", "willow",
    "marble", "pebble", "harvest", "signal", "blossom", "thicket", "ribbon", "quarry",
    "cascade", "mirage", "trellis", "spindle", "granite", "horizon", "lattice", "cavern",
    "orbit", "satchel"
]


def random_slug(n_words=2):
    """Build a docker-safe lowercase slug like 'swift-otter-3f2a'."""
    words = [random.choice(ADJECTIVES), random.choice(NOUNS)]
    suffix = "".join(random.choices(
        string.ascii_lowercase + string.digits, k=4))
    return "-".join(words[:n_words] + [suffix])


def random_version():
    """Random semver-ish version tag, e.g. 'v2.7.13' or 'v0.1.0-beta.4'."""
    major, minor, patch = (random.randint(0, 5) for _ in range(3))
    version = f"v{major}.{minor}.{patch}"
    x = random.random()
    if x < 0.3:
        version += f"-beta.{random.randint(1, 9)}"
    elif 0.3 <= x < 0.5:
        version += f"-alpine"
    elif 0.5 <= x < 0.7:
        version += f"-slim"
    elif 0.7 <= x < 1:
        version += f"-bookworm"

    return version


def run(cmd, **kwargs):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result


def check_docker():
    try:
        run(["docker", "info"], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    except Exception:
        print("ERROR: Docker doesn't seem to be running or isn't installed.")
        sys.exit(1)


def ensure_base_image():
    run(["docker", "pull", BASE_IMAGE])


def build_unique_image(full_tag: str):
    """Build a tiny derived image with a random file baked in, so each
    push produces a genuinely unique image (different digest/size)."""
    random_blob = "".join(random.choices(
        string.ascii_letters + string.digits, k=64))
    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_path = os.path.join(tmpdir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(
                f"FROM {BASE_IMAGE}\n"
                f"LABEL generated=random-image-generator\n"
                f"RUN echo '{random_blob}' > /random_marker.txt\n"
            )
        run(["docker", "build", "-t", full_tag, tmpdir])


def tag_base_image(full_tag: str):
    run(["docker", "tag", BASE_IMAGE, full_tag])


def push_image(full_tag: str):
    run(["docker", "push", full_tag])


def cleanup_image(full_tag: str):
    subprocess.run(
        ["docker", "rmi", "-f", full_tag],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    check_docker()
    ensure_base_image()

    total = NUM_NAMESPACES * NUM_NAMES_PER_NAMESPACE * NUM_VERSIONS_PER_NAME
    print(f"\nPlanning to push {total} image tags to {REGISTRY}\n")

    pushed = []
    for _ in range(NUM_NAMESPACES):
        namespace = random_slug(n_words=1)  # e.g. "swift-9f3a"
        for _ in range(NUM_NAMES_PER_NAMESPACE):
            image_name = random_slug(n_words=2)  # e.g. "bold-comet-7c1e"
            for _ in range(NUM_VERSIONS_PER_NAME):
                version = random_version()
                full_tag = f"{REGISTRY}/{namespace}/{image_name}:{version}"
                print(f"\n--- Building/pushing {full_tag} ---")

                if UNIQUE_CONTENT:
                    build_unique_image(full_tag)
                else:
                    tag_base_image(full_tag)

                push_image(full_tag)
                pushed.append(full_tag)

                if CLEANUP_LOCAL_IMAGES:
                    cleanup_image(full_tag)

    print(f"\nDone. Pushed {len(pushed)} image tags to {REGISTRY}:\n")
    for tag in pushed:
        print(f"  {tag}")


if __name__ == "__main__":
    main()
