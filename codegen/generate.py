#!/usr/bin/env python3
"""
OpenAPI → Python code generator for LOLZTEAM API wrappers.

Usage:
    python generate.py --schema forum.json --output ../lolzteam/forum/_generated.py --class ForumAPI
    python generate.py --schema market.json --output ../lolzteam/market/_generated.py --class MarketAPI
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_PYTHON_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield", "type", "filter", "list", "dict", "id",
    "format", "input", "open", "print", "object",
}

_OAS_TO_PY = {
    "integer": "int",
    "number": "float",
    "string": "str",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


def safe_name(name: str) -> str:
    """Convert an arbitrary string to a safe Python identifier."""
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if name and name[0].isdigit():
        name = "_" + name
    if name in _PYTHON_KEYWORDS:
        name = name + "_"
    return name


def camel_to_snake(name: str) -> str:
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
    return name.lower()


def path_to_method_name(path: str, http_method: str) -> str:
    """
    /users/{user_id}/followers  GET  →  get_users_user_id_followers
    """
    parts = [p for p in path.strip("/").split("/") if p]
    cleaned = []
    for p in parts:
        if p.startswith("{") and p.endswith("}"):
            cleaned.append("by_" + safe_name(p[1:-1]))
        else:
            cleaned.append(safe_name(camel_to_snake(p)))
    return http_method.lower() + "_" + "_".join(cleaned) if cleaned else http_method.lower()


def operation_id_to_method(op_id: str) -> str:
    return safe_name(camel_to_snake(op_id))


def oas_type(schema: dict[str, Any] | None) -> str:
    if not schema:
        return "Any"
    ref = schema.get("$ref")
    if ref:
        return ref.split("/")[-1]
    t = schema.get("type")
    fmt = schema.get("format", "")
    if t == "integer":
        return "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    if t == "string":
        if fmt in ("date", "date-time"):
            return "str"
        return "str"
    if t == "array":
        items = schema.get("items", {})
        return f"List[{oas_type(items)}]"
    if t == "object":
        return "Dict[str, Any]"
    if "anyOf" in schema or "oneOf" in schema or "allOf" in schema:
        return "Any"
    return "Any"


def required_set(params: list[dict]) -> set[str]:
    return {p["name"] for p in params if p.get("required", False)}


def _resolve_ref(ref: str, spec: dict) -> dict:
    """Resolve a JSON $ref like '#/components/parameters/Foo'."""
    parts = ref.lstrip("#/").split("/")
    node = spec
    for part in parts:
        node = node.get(part, {})
    return node


def collect_params(operation: dict, path_item: dict, spec: dict | None = None) -> list[dict]:
    """Merge path-level and operation-level parameters (operation wins).
    Resolves $ref entries when spec is provided.
    """
    spec = spec or {}
    merged: dict[str, dict] = {}

    def resolve(p: dict) -> dict:
        if "$ref" in p:
            resolved = _resolve_ref(p["$ref"], spec)
            return resolved if resolved else {}
        return p

    for p in path_item.get("parameters", []):
        p = resolve(p)
        if p.get("name"):
            merged[p["name"]] = p
    for p in operation.get("parameters", []):
        p = resolve(p)
        if p.get("name"):
            merged[p["name"]] = p
    return list(merged.values())


def build_docstring(summary: str | None, description: str | None,
                    params: list[dict], body_props: dict | None, indent: int) -> str:
    pad = " " * indent
    lines: list[str] = []
    first_line = summary or description or ""
    if first_line:
        lines.append(f'"""{first_line}')
    else:
        lines.append('"""')

    all_described: list[tuple[str, str, str]] = []  # (name, type, desc)
    for p in params:
        pname = safe_name(p["name"])
        ptype = oas_type(p.get("schema"))
        pdesc = p.get("description", "").replace("\n", " ")
        all_described.append((pname, ptype, pdesc))

    if body_props:
        for bname, bschema in body_props.items():
            bdesc = bschema.get("description", "").replace("\n", " ")
            btype = oas_type(bschema)
            all_described.append((safe_name(bname), btype, bdesc))

    if all_described:
        lines.append("")
        lines.append("Args:")
        for nm, tp, dc in all_described:
            lines.append(f"    {nm} ({tp}): {dc}")

    lines.append('"""')
    return ("\n" + pad).join(lines)


# ---------------------------------------------------------------------------
# main generator
# ---------------------------------------------------------------------------

def generate(schema_path: Path, output_path: Path, class_name: str) -> None:
    with open(schema_path, encoding="utf-8") as f:
        spec: dict[str, Any] = json.load(f)

    paths: dict[str, dict] = spec.get("paths", {})
    components = spec.get("components", {})
    schemas = components.get("schemas", {})

    # ---- collect all operations -----------------------------------------
    operations: list[dict[str, Any]] = []
    for path, path_item in paths.items():
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if not operation:
                continue
            op_id = operation.get("operationId")
            method_name = (
                operation_id_to_method(op_id) if op_id
                else path_to_method_name(path, method)
            )
            params = collect_params(operation, path_item, spec=spec)
            # separate by location
            path_params = [p for p in params if p.get("in") == "path"]
            query_params = [p for p in params if p.get("in") == "query"]
            header_params = [p for p in params if p.get("in") == "header"]

            # request body
            body_schema: dict | None = None
            body_props: dict | None = None
            body_required: set[str] = set()
            rb = operation.get("requestBody", {})
            if rb:
                content = rb.get("content", {})
                for media_type in ("application/json",
                                   "application/x-www-form-urlencoded",
                                   "multipart/form-data"):
                    mt = content.get(media_type)
                    if mt:
                        body_schema = mt.get("schema", {})
                        ref = body_schema.get("$ref")
                        if ref:
                            ref_name = ref.split("/")[-1]
                            body_schema = schemas.get(ref_name, {})
                        body_props = body_schema.get("properties", {})
                        body_required = set(body_schema.get("required", []))
                        break

            # build signature arg list
            # order: path params (required), then query required, then body required,
            #        then optional query, then optional body
            req_path = [p for p in path_params]  # always required
            req_query = [p for p in query_params if p.get("required")]
            opt_query = [p for p in query_params if not p.get("required")]

            req_body: list[tuple[str, dict]] = []
            opt_body: list[tuple[str, dict]] = []
            if body_props:
                for bname, bschema in body_props.items():
                    if bname in body_required:
                        req_body.append((bname, bschema))
                    else:
                        opt_body.append((bname, bschema))

            operations.append({
                "method_name": method_name,
                "http_method": method.upper(),
                "path": path,
                "summary": operation.get("summary"),
                "description": operation.get("description"),
                "path_params": req_path,
                "req_query": req_query,
                "opt_query": opt_query,
                "req_body": req_body,
                "opt_body": opt_body,
                "has_body": bool(body_props is not None),
                "body_props": body_props,
                "body_required": body_required,
            })

    # ---- render code -------------------------------------------------------
    lines: list[str] = [
        "# This file is AUTO-GENERATED by codegen/generate.py",
        "# Do not edit manually – re-run the generator instead.",
        "from __future__ import annotations",
        "",
        "from typing import Any, Dict, List, Optional",
        "",
        "from .._core.mixin import ApiMixin",
        "",
        "",
        f"class {class_name}(ApiMixin):",
        '    """Auto-generated API methods."""',
        "",
    ]

    seen_names: dict[str, int] = {}

    for op in operations:
        name = op["method_name"]
        # deduplicate
        if name in seen_names:
            seen_names[name] += 1
            name = f"{name}_{seen_names[name]}"
        else:
            seen_names[name] = 0

        # --- build signature -----------------------------------------------
        sig_parts = ["self"]
        for p in op["path_params"]:
            pn = safe_name(p["name"])
            pt = oas_type(p.get("schema"))
            sig_parts.append(f"{pn}: {pt}")
        for p in op["req_query"]:
            pn = safe_name(p["name"])
            pt = oas_type(p.get("schema"))
            sig_parts.append(f"{pn}: {pt}")
        for bname, bschema in op["req_body"]:
            bn = safe_name(bname)
            bt = oas_type(bschema)
            sig_parts.append(f"{bn}: {bt}")
        for p in op["opt_query"]:
            pn = safe_name(p["name"])
            pt = oas_type(p.get("schema"))
            sig_parts.append(f"{pn}: Optional[{pt}] = None")
        for bname, bschema in op["opt_body"]:
            bn = safe_name(bname)
            bt = oas_type(bschema)
            sig_parts.append(f"{bn}: Optional[{bt}] = None")

        sig = ", ".join(sig_parts)
        lines.append(f"    def {name}({sig}) -> Any:")

        # --- docstring -------------------------------------------------------
        all_params_for_doc = (
            op["path_params"] + op["req_query"] + op["opt_query"]
        )
        lines.append(f"        {build_docstring(op['summary'], op['description'], all_params_for_doc, op['body_props'], 8)}")

        # --- body ------------------------------------------------------------
        # build path
        py_path = op["path"]
        for p in op["path_params"]:
            pn = safe_name(p["name"])
            py_path = py_path.replace(f"{{{p['name']}}}", f"{{{pn}}}")
        lines.append(f'        _path = f"{py_path}"')

        # query dict
        q_names = [safe_name(p["name"]) for p in op["req_query"] + op["opt_query"]]
        q_orig_names = [p["name"] for p in op["req_query"] + op["opt_query"]]
        if q_names:
            items = ", ".join(
                f'"{orig}": {pn}' for orig, pn in zip(q_orig_names, q_names)
            )
            lines.append(f"        _params = {{{items}}}")
            lines.append("        _params = {k: v for k, v in _params.items() if v is not None}")
        else:
            lines.append("        _params = {}")

        # body dict
        if op["body_props"] is not None:
            all_body = op["req_body"] + op["opt_body"]
            if all_body:
                items = ", ".join(
                    f'"{bname}": {safe_name(bname)}' for bname, _ in all_body
                )
                lines.append(f"        _data = {{{items}}}")
                lines.append("        _data = {k: v for k, v in _data.items() if v is not None}")
            else:
                lines.append("        _data = {}")
            lines.append(f'        return self._request("{op["http_method"]}", _path, params=_params, json=_data)')
        else:
            lines.append(f'        return self._request("{op["http_method"]}", _path, params=_params)')

        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅  Generated {len(operations)} methods → {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Python API wrapper from OpenAPI schema")
    parser.add_argument("--schema", required=True, help="Path to OpenAPI JSON schema")
    parser.add_argument("--output", required=True, help="Output Python file path")
    parser.add_argument("--class", dest="class_name", default="GeneratedAPI",
                        help="Name of the generated class")
    args = parser.parse_args()

    schema_path = Path(args.schema)
    if not schema_path.exists():
        print(f"❌  Schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(1)

    generate(schema_path, Path(args.output), args.class_name)


if __name__ == "__main__":
    main()
