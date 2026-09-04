import re
import json
from typing import List, Dict

KNOWN_VULNERABILITIES = {
    "log4j": {"1.2": "CVE-2021-4104", "2.14": "CVE-2021-44228"},
    "requests": {"2.0": "CVE-2018-18074"},
    "urllib3": {"1.26.4": "CVE-2021-33503"},
    "express": {"4.15": "CVE-2022-24999"}
}

def check_dependencies(file_content: str, filename: str) -> List[Dict]:
    """Analyze dependency files for known vulnerabilities.
    NOTE: In production, this would integrate with the OSV.dev API.
    """
    if "requirements.txt" in filename:
        deps = _parse_requirements(file_content)
    elif "package.json" in filename:
        deps = _parse_package_json(file_content)
    else:
        return []
    
    findings = []
    for dep in deps:
        vulns = _check_known_vulnerabilities(dep["name"], dep["version"])
        for v in vulns:
            findings.append({
                "package": dep["name"],
                "version": dep["version"],
                "vulnerability": v["cve"],
                "message": f"Critical vulnerability {v['cve']} found in {dep['name']}@{dep['version']}"
            })
    return findings

def _parse_requirements(content: str) -> List[Dict]:
    deps = []
    for line in content.splitlines():
        line = line.split('#')[0].strip()
        if not line:
            continue
        match = re.match(r"^([a-zA-Z0-9_\-]+)(?:==|>=|<=|~=)(.+)$", line)
        if match:
            deps.append({"name": match.group(1).lower(), "version": match.group(2)})
        elif re.match(r"^[a-zA-Z0-9_\-]+$", line):
            deps.append({"name": line.lower(), "version": "latest"})
    return deps

def _parse_package_json(content: str) -> List[Dict]:
    deps = []
    try:
        data = json.loads(content)
        all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for name, version in all_deps.items():
            clean_version = re.sub(r'^[^\d]', '', version)
            deps.append({"name": name.lower(), "version": clean_version})
    except json.JSONDecodeError:
        pass
    return deps

def _check_known_vulnerabilities(package: str, version: str) -> List[Dict]:
    vulns = []
    if package in KNOWN_VULNERABILITIES:
        pkg_vulns = KNOWN_VULNERABILITIES[package]
        for v_version, cve in pkg_vulns.items():
            if version.startswith(v_version):
                vulns.append({"cve": cve})
    return vulns
