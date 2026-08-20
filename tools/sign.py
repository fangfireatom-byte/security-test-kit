#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
security-test-kit / tools/sign.py
=================================
通用签名/加密命令行工具。Agent 调用，处理它做不了的密码学运算。

定位：这是**可选的通用脚手架**，覆盖常见算法组合（md5_concat/hmac_sha256/aes_ecb/rsa_wrap 等）。
Agent 可直接用（配 signer.yaml）、可改写扩展、也可弃用后针对非常规算法自写脚本放 tools/ 下。
本工具不替 Agent 决策签名机制——签名算法由 Agent 读目标前端 JS/文档后发现并填入 signer.yaml。

设计：
- 读 config/signer.yaml 描述的签名/加密机制，按 algorithm 分派
- 只做运算，不发请求、不限速、不判定（那些是 Agent 的活）
- 无签名项目不调用本脚本（零依赖）

用法（签名模式）：
    python tools/sign.py --config config/signer.yaml \
        --method POST --path /api/user/login.do \
        --body '{"phone":"130****","password":"***"}' --token "" --uid ""

用法（解密模式）：
    python tools/sign.py --config config/signer.yaml --decrypt \
        --resp-headers '{"Aes-Key":"..."}' --resp-body '{"data":"..."}'

输出：JSON 到 stdout，Agent 拿来拼请求 / 读响应。
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import random
import string
import sys
import time
import urllib.parse


# ── 配置加载 ──────────────────────────────────────────────
def load_config(path):
    try:
        import yaml
    except ImportError:
        die("需要 pyyaml：pip install pyyaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def die(msg, code=1):
    print(json.dumps({"_error": msg}, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


# ── 值生成器 ──────────────────────────────────────────────
def now_ms():
    return str(int(time.time() * 1000))


def random_base36(n):
    chars = string.digits + string.ascii_lowercase
    return "".join(random.choice(chars) for _ in range(n))


def random_upper(n):
    chars = string.digits + string.ascii_uppercase
    return "".join(random.choice(chars) for _ in range(n))


GEN = {"now_ms": now_ms, "random_base36_6": lambda: random_base36(6),
       "random_base36_8": lambda: random_base36(8), "random_upper_16": lambda: random_upper(16)}


# ── 可选块处理：formula 里 [xxx] 表示 xxx 里的 {var} 有值才保留 ──
def eval_formula(formula, values):
    """处理 {ts}-{nonce}[-{uid}]|...|[token] 这类含可选块的公式"""
    import re
    # 1. 处理可选块 [...]：块内所有 {var} 都有值 → 保留块内容（去括号）并替换；否则删除整个块
    def repl_block(m):
        block = m.group(1)
        vars_in_block = re.findall(r"\{(\w+)\}", block)
        if all(values.get(v) for v in vars_in_block):
            return block  # 保留，下一步替换 {var}
        return ""  # 删除整个块
    formula = re.sub(r"\[([^\[\]]*)\]", repl_block, formula)
    # 2. 替换 {var}
    def repl_var(m):
        return str(values.get(m.group(1), ""))
    return re.sub(r"\{(\w+)\}", repl_var, formula)


# ── 签名算法 ──────────────────────────────────────────────
def sign_md5_concat(formula, values, secret):
    s = eval_formula(formula, values)
    return hashlib.md5(s.encode()).hexdigest()


def sign_hmac_sha256(formula, values, secret):
    if not secret:
        die("hmac_sha256 需要 secret")
    s = eval_formula(formula, values)
    key = secret.encode()
    return hmac.new(key, s.encode(), hashlib.sha256).hexdigest()


def sign_jwt(values, secret, fields):
    # 简易 HS256；复杂 RS256/ES256 需扩展
    die("jwt 签名需按项目自行扩展（tools/sign.py sign_jwt）")


SIGNERS = {"md5_concat": sign_md5_concat, "hmac_sha256": sign_hmac_sha256,
           "jwt": sign_jwt, "none": lambda *a: "", "custom": lambda *a: die("custom 签名需自行扩展")}


# ── 加密 ──────────────────────────────────────────────────
def aes_encrypt_ecb(plaintext, key):
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    cipher = AES.new(key.encode() if isinstance(key, str) else key, AES.MODE_ECB)
    return cipher.encrypt(pad(plaintext.encode(), 16))


def aes_encrypt_gcm(plaintext, key):
    from Crypto.Cipher import AES
    enc = AES.new(key.encode() if isinstance(key, str) else key, AES.MODE_GCM)
    ct, tag = enc.encrypt_and_digest(plaintext.encode())
    return base64.b64encode(enc.nonce + tag + ct).decode()


def rsa_wrap(aes_key, pubkey_pem):
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    from Crypto.Random import get_random_bytes
    key = RSA.import_key(open(pubkey_pem).read() if os.path.isfile(pubkey_pem) else pubkey_pem)
    # PKCS1_v1_5 encrypt；部分项目用 PKCS1_OAEP，按需扩展
    cipher = PKCS1_v1_5.new(key)
    return cipher.encrypt(aes_key.encode() if isinstance(aes_key, str) else aes_key)


def rsa_pub_decrypt(ciphertext, pubkey_pem):
    """用公钥做 RSA 运算恢复明文（服务端用私钥加密，客户端用公钥解密）"""
    from Crypto.PublicKey import RSA
    from Crypto.Util.number import bytes_to_long, long_to_bytes
    key = RSA.import_key(open(pubkey_pem).read() if os.path.isfile(pubkey_pem) else pubkey_pem)
    c = bytes_to_long(ciphertext)
    m = pow(c, key.e, key.n)
    return long_to_bytes(m)


# ── 主流程：签名模式 ──────────────────────────────────────
def build_request(cfg, method, path, body_str, token, uid):
    sign_cfg = cfg.get("sign", {})
    enc_cfg = cfg.get("encrypt", {})
    const = cfg.get("constants", {}) or {}

    # 生成 ts/nonce
    fields_cfg = sign_cfg.get("fields", {}) or {}
    ts = now_ms()
    nonce = random_base36(6)
    # 用户传入的 uid/token
    uid = uid or ""
    token = token or ""

    # formula 的 values
    values = {
        "ts": ts, "nonce": nonce, "uid": uid, "token": token,
        "method": method.lower(), "path": path, "payload": body_str,
        "app": const.get("app_type", ""), "device": const.get("device_type", ""),
        "brand": const.get("brand", ""), "os": const.get("os", ""),
    }
    # 也注入 fields 里定义的其它 gen 值
    for k, spec in fields_cfg.items():
        if k not in values and isinstance(spec, dict) and "gen" in spec:
            gen = spec["gen"]
            values[k] = GEN[gen]() if gen in GEN else ""

    # 签名
    algorithm = sign_cfg.get("algorithm", "none")
    secret_raw = sign_cfg.get("secret", "none")
    secret = resolve_secret(secret_raw)
    sign_val = SIGNERS.get(algorithm, lambda *a: "")(sign_cfg.get("formula", ""), values, secret)

    # body 加密
    payload = body_str
    encrypted_body_b64 = ""
    aes_key = ""
    wrapped_key_b64 = ""
    if enc_cfg.get("enabled"):
        aes_key = random_upper(16)
        etype = enc_cfg.get("type", "none")
        if etype == "aes_ecb":
            ct = aes_encrypt_ecb(payload, aes_key)
        elif etype == "aes_gcm":
            ct = aes_encrypt_gcm(payload, aes_key).encode()
        else:
            ct = payload.encode()
        encrypted_body_b64 = base64.b64encode(ct).decode()
        if enc_cfg.get("key_transport") == "rsa_wrap":
            wrapped = rsa_wrap(aes_key, enc_cfg["rsa_pubkey_file"])
            wrapped_key_b64 = base64.b64encode(wrapped).decode()

    # 组装 headers
    headers = {}
    for k, spec in fields_cfg.items():
        if not isinstance(spec, dict):
            continue
        hname = spec.get("name")
        if not hname:
            continue
        if spec.get("optional") and not values.get(k):
            continue
        headers[hname] = str(values.get(k, ""))
    if sign_val:
        headers["sign"] = sign_val
    if enc_cfg.get("enabled"):
        headers["encrypted"] = "1"
        if wrapped_key_b64:
            headers["aes-key"] = wrapped_key_b64
    # 注入设备指纹/常量为 headers（key 下划线转连字符：app_type→app-type 等）
    for k, v in const.items():
        if v not in ("", None):
            headers.setdefault(k.replace("_", "-"), str(v))
    if uid and not _is_whitelist(cfg, path):
        headers[_field_name(fields_cfg, "uid", "uid")] = uid
    if token and not _is_whitelist(cfg, path):
        headers[_field_name(fields_cfg, "token", "token")] = token

    # 组装 body / url
    if method.upper() == "GET":
        body_out = ""
        if encrypted_body_b64:
            url_suffix = "?data=" + urllib.parse.quote(encrypted_body_b64)
        else:
            url_suffix = ""
    else:
        if encrypted_body_b64:
            body_out = "data=" + urllib.parse.quote(encrypted_body_b64)
        else:
            body_out = payload
        url_suffix = ""

    return {
        "headers": headers,
        "body": body_out,
        "url_suffix": url_suffix,
        "decrypted_preview": payload,
        "_sign_raw": sign_val,
    }


def resolve_secret(raw):
    if not raw or raw == "none":
        return None
    if raw.startswith("env:"):
        return os.environ.get(raw[4:], "")
    if raw.startswith("file:"):
        try:
            return open(raw[5:]).read().strip()
        except Exception:
            return None
    return raw


def _is_whitelist(cfg, path):
    wl = cfg.get("whitelist_paths") or []
    return any(path.startswith(p) for p in wl)


def _field_name(fields_cfg, key, default):
    spec = fields_cfg.get(key, {})
    return spec.get("name", default) if isinstance(spec, dict) else default


# ── 主流程：解密模式 ──────────────────────────────────────
def decrypt_response(cfg, resp_headers_json, resp_body_json):
    rd = cfg.get("response_decrypt", {}) or {}
    if not rd.get("enabled"):
        return {"decrypted": None, "note": "response_decrypt.enabled=false"}
    method = rd.get("method", "none")
    resp_headers = json.loads(resp_headers_json) if resp_headers_json else {}
    resp_body = json.loads(resp_body_json) if isinstance(resp_body_json, str) else resp_body_json

    aes_key_b64 = resp_headers.get(rd.get("aes_key_header", "Aes-Key"), "")
    if not aes_key_b64:
        return {"decrypted": resp_body, "note": "无 Aes-Key 头，可能未加密"}
    enc_key = base64.b64decode(aes_key_b64)

    enc_cfg = cfg.get("encrypt", {}) or {}
    pubkey_file = enc_cfg.get("rsa_pubkey_file", "")

    if method == "rsa_pub_decrypt":
        aes_key = rsa_pub_decrypt(enc_key, pubkey_file)
        aes_key = aes_key[-16:].decode("ascii", errors="ignore")
    elif method == "aes_shared":
        aes_key = resolve_secret(enc_cfg.get("shared_key", "none"))
    else:
        return {"decrypted": resp_body, "note": f"method={method} 未实现"}

    data_field = resp_body.get("data") if isinstance(resp_body, dict) else None
    if isinstance(data_field, str):
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import unpad
            enc_data = base64.b64decode(data_field)
            cipher = AES.new(aes_key.encode(), AES.MODE_ECB)
            plain = unpad(cipher.decrypt(enc_data), 16).decode()
            resp_body["data"] = json.loads(plain)
        except Exception as e:
            resp_body["_decrypt_error"] = str(e)
    return {"decrypted": resp_body, "aes_key_used": aes_key}


# ── CLI ───────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="security-test-kit 通用签名/加密工具")
    ap.add_argument("--config", default="config/signer.yaml", help="signer.yaml 路径")
    ap.add_argument("--decrypt", action="store_true", help="解密响应模式")
    ap.add_argument("--method", default="GET")
    ap.add_argument("--path", default="")
    ap.add_argument("--body", default="{}")
    ap.add_argument("--token", default="")
    ap.add_argument("--uid", default="")
    ap.add_argument("--resp-headers", default="", help="响应头 JSON")
    ap.add_argument("--resp-body", default="", help="响应体 JSON")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if not cfg.get("enabled", False):
        die("signer.yaml enabled=false，本项目无签名层，无需调用 sign.py")

    if args.decrypt:
        out = decrypt_response(cfg, args.resp_headers, args.resp_body)
    else:
        out = build_request(cfg, args.method, args.path, args.body, args.token, args.uid)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
