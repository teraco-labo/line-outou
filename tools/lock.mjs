#!/usr/bin/env node
// てらこ図書館の鍵：テキストを番号（パスワード）で暗号化して .lock にする（2026-10-10）。
// 方式は講師用（~/.claude/skills/teraco-slide/templates/lock_for_teacher.mjs）と同じ PBKDF2-SHA256 60万回 + AES-GCM。
// 番号はファイルにだけ置き、ここにも会話にも書かない。
// 使い方：node tools/lock.mjs --pass-file <番号のファイル> <入力> <出力 .lock>
import { readFileSync, writeFileSync } from 'node:fs';
import { webcrypto as crypto } from 'node:crypto';

const a = process.argv.slice(2);
const i = a.indexOf('--pass-file');
if (i < 0 || a.length < 4) { console.error('使い方: node tools/lock.mjs --pass-file <番号のファイル> <入力> <出力>'); process.exit(1); }
const passFile = a[i + 1]; const [src, out] = a.filter((_, k) => k !== i && k !== i + 1);
let pass;
try { pass = readFileSync(passFile, 'utf8').trim(); } catch { console.error('番号のファイルがありません: ' + passFile); process.exit(2); }
if (!pass) { console.error('番号のファイルが空です'); process.exit(3); }
const ITER = 600000, enc = new TextEncoder();
const salt = crypto.getRandomValues(new Uint8Array(16)), iv = crypto.getRandomValues(new Uint8Array(12));
const base = await crypto.subtle.importKey('raw', enc.encode(pass), 'PBKDF2', false, ['deriveKey']);
const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt, iterations: ITER, hash: 'SHA-256' }, base,
  { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
const data = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode(readFileSync(src, 'utf8')));
const b64 = (u) => Buffer.from(u).toString('base64');
writeFileSync(out, JSON.stringify({ v: 1, iter: ITER, salt: b64(salt), iv: b64(iv), data: b64(new Uint8Array(data)) }));
