from __future__ import annotations

from itertools import chain
import json
import os
import urllib.request


v3_CHANNEL = "https://packagecontrol.io/channel_v3.json"
v4_CHANNEL = "https://packagecontrol.github.io/channel/channel_v4.json"
OUTPUT_FILE = os.path.abspath("channel.json")


def main():
    v3_channel = http_get_json(v3_CHANNEL)
    v4_channel = http_get_json(v4_CHANNEL)

    dependencies = v3_channel.pop('dependencies_cache', {})
    for library in chain(*dependencies.values()):
        del library['load_order']
        for release in library['releases']:
            release['python_versions'] = ['3.3']

    channel = {
        "schema_version": "4.0.0",
        "repositories": v4_channel["repositories"] + v3_channel["repositories"],
        "packages_cache": v3_channel["packages_cache"] | v4_channel["packages_cache"],
        "libraries_cache": dependencies | v4_channel["libraries_cache"],
    }

    for key, value in channel.items():
        match key:
            case "packages_cache" | "libraries_cache":
                for repo_url, packages in value.items():
                    packages.sort(key=lambda p: p["name"])
                    for p in packages:
                        if "releases" in p:
                            p["releases"].sort(
                                key=lambda r: (
                                    r.get("date") or r.get("version"),
                                    r.get("platforms"),
                                    r.get("sublime_text")
                                )
                            )

    with open(OUTPUT_FILE, "w") as f:
        json.dump(channel, f)


def http_get_json(location: str) -> dict:
    json_string = http_get(location)
    return json.loads(json_string)


def http_get(location: str) -> str:
    req = urllib.request.Request(
        location,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')


if __name__ == "__main__":
    main()
