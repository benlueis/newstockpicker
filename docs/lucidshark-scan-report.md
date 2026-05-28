# LucidShark 代码审查报告

## 📊 扫描状态

✅ **扫描完成** - 发现 4 个安全问题

## 🔍 发现的问题

### 1. 高严重性 - Dockerfile 缺少 USER 指令

**文件:** `Dockerfile:39`
**问题:** By not specifying a USER, a program in the container may run as 'root'. This is a security hazard. If an attacker can control a process running as root, they may have control over the container. Ensure that the last USER in a Dockerfile is a USER other than 'root'.

**当前代码:**
```dockerfile
CMD ["tail", "-f", "/dev/null"]
```

**建议修复:**
```dockerfile
USER non-root
CMD ["tail", "-f", "/dev/null"]
```

**参考:** https://owasp.org/Top10/A04_2021-Insecure_Design

---

### 2. 中严重性 - notify.py 动态 urllib 使用

**文件:** `scripts/notify.py:34`
**问题:** Detected a dynamic value being used with urllib. urllib supports 'file://' schemes, so a dynamic value controlled by a malicious actor may allow them to read arbitrary files. Audit uses of urllib calls to ensure user data cannot control the URLs, or consider using the 'requests' library instead.

**当前代码:**
```python
with urllib.request.urlopen(req, timeout=10) as resp:
```

**建议修复:** 使用 `requests` 库替代 `urllib`

**参考:** https://cwe.mitre.org/data/definitions/939.html

---

### 3. 低严重性 - tracker.py 使用 HTTP 请求

**文件:** `backtest/tracker.py:32`
**问题:** Detected a request using 'http://'. This request will be unencrypted, and attackers could listen into traffic on the network and be able to obtain sensitive information. Use 'https://' instead.

**当前代码:**
```python
resp = requests.get(url, headers=SINA_HEADERS, timeout=10)
```

**说明:** 新浪财经 API (`hq.sinajs.cn`) 仅支持 HTTP，不支持 HTTPS。这是已知的第三方 API 限制。

---

### 4. 低严重性 - cache_manager.py 使用 HTTP 请求

**文件:** `scripts/cache_manager.py:126`
**问题:** Detected a request using 'http://'. This request will be unencrypted, and attackers could listen into traffic on the network and be able to obtain sensitive information. Use 'https://' instead.

**当前代码:**
```python
r = requests.get(url, timeout=10)
```

**说明:** 腾讯行情 API (`web.ifzq.gtimg.cn`) 仅支持 HTTP，不支持 HTTPS。这是已知的第三方 API 限制。

---

## 📊 问题统计

| 严重性 | 数量 | 状态 |
|--------|------|------|
| 高 | 1 | 需要修复 |
| 中 | 1 | 建议修复 |
| 低 | 2 | 已知限制 |
| **总计** | **4** | - |

## 🎯 建议修复优先级

### 高优先级
1. **Dockerfile 缺少 USER 指令** - 添加非 root 用户运行容器

### 中优先级
2. **notify.py 动态 urllib 使用** - 使用 `requests` 库替代

### 低优先级
3. **HTTP 请求问题** - 这是第三方 API 的限制，无法修复

## 📝 修复建议

### 1. Dockerfile 修复
```dockerfile
# 在 CMD 之前添加
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser
```

### 2. notify.py 修复
```python
import requests

def send(title, body, group="stock-scan", url=None):
    bark_url = os.environ.get(BARK_URL_ENV)
    if not bark_url:
        return False
    
    payload = {"title": title, "body": body, "group": group}
    if url:
        payload["url"] = url
    
    try:
        resp = requests.post(bark_url.rstrip("/"), json=payload, timeout=10)
        return 200 <= resp.status_code < 300
    except requests.RequestException:
        return False
```

## 📚 参考资源

- [OWASP Top 10 - A04:2021 Insecure Design](https://owasp.org/Top10/A04_2021-Insecure_Design)
- [CWE-939: Improper Authorization in Handler for Custom URL Scheme](https://cwe.mitre.org/data/definitions/939.html)
- [LucidShark 文档](https://lucidshark.com/docs)

---

**扫描工具:** LucidShark v0.7.8
**扫描时间:** 2026-05-28 14:12:24
**扫描结果:** 4 个问题（1 高、1 中、2 低）