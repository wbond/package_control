from __future__ import annotations

import json
import os
import urllib.request


INPUT_FILE = "https://packagecontrol.io/channel_v3.json"
OUTPUT_FILE = os.path.abspath("channel.json")


def main():
    channel = http_get_json(INPUT_FILE)
    for key, value in channel.items():
        match key:
            case "repositories": value.sort()
            case "packages_cache" | "dependencies_cache":
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
