# SurfScreen REST API 가이드

## 🚀 시작하기

### 서버 시작

```bash
# 개발 모드 (자동 리로드, 인증 비활성화)
surfscreen api start --debug --reload

# 프로덕션 모드
surfscreen api start --host 0.0.0.0 --port 8000 --workers 4
```

### API 키 발급

```bash
# 새 API 키 생성
surfscreen api generate-key

# 환경변수 설정
export SURFSCREEN_API_KEY=your-generated-key

# 또는 .env 파일에 추가
echo "SURFSCREEN_API_KEY=your-key" >> .env
```

---

## 🔐 인증

모든 API 요청에 `X-API-Key` 헤더 필요:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/jobs
```

Python:

```python
import requests

headers = {"X-API-Key": "your-api-key"}
response = requests.get("http://localhost:8000/api/v1/jobs", headers=headers)
```

> ⚠️ `--debug` 모드에서는 인증이 비활성화됨

---

## 📚 엔드포인트

### Health

| Method | Path            | Description          |
| ------ | --------------- | -------------------- |
| GET    | `/health`       | 서버 상태 확인       |
| GET    | `/health/ready` | 준비 상태 확인 (K8s) |
| GET    | `/health/live`  | 생존 상태 확인 (K8s) |

### Jobs

| Method | Path                         | Description       |
| ------ | ---------------------------- | ----------------- |
| GET    | `/api/v1/jobs`               | Job 목록 조회     |
| GET    | `/api/v1/jobs/{id}`          | Job 상세 조회     |
| DELETE | `/api/v1/jobs/{id}`          | Job 취소          |
| GET    | `/api/v1/jobs/{id}/result`   | 결과 JSON         |
| GET    | `/api/v1/jobs/{id}/download` | 결과 ZIP 다운로드 |
| GET    | `/api/v1/jobs/{id}/logs`     | 로그 조회         |

### Screening

| Method | Path                            | Description       |
| ------ | ------------------------------- | ----------------- |
| POST   | `/api/v1/screening`             | 스크리닝 Job 생성 |
| GET    | `/api/v1/screening/{id}/result` | 스크리닝 결과     |
| GET    | `/api/v1/screening/{id}/report` | HTML 리포트       |

### MD Simulation

| Method | Path                         | Description   |
| ------ | ---------------------------- | ------------- |
| POST   | `/api/v1/md`                 | MD Job 생성   |
| GET    | `/api/v1/md/{id}/result`     | MD 결과       |
| GET    | `/api/v1/md/{id}/trajectory` | 궤적 다운로드 |
| GET    | `/api/v1/md/{id}/report`     | HTML 리포트   |

---

## 📝 사용 예제

### 스크리닝 Job 생성

```bash
curl -X POST "http://localhost:8000/api/v1/screening" \
  -H "X-API-Key: your-key" \
  -F "surface=@Cu_111.xyz" \
  -F "molecules=@CO.xyz" \
  -F "molecules=@H2O.xyz" \
  -F 'config={"engine":"mace","max_configs":30}'
```

Python:

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/screening",
    headers={"X-API-Key": "your-key"},
    files=[
        ("surface", open("Cu_111.xyz", "rb")),
        ("molecules", open("CO.xyz", "rb")),
    ],
    data={"config": '{"engine":"mace","max_configs":30}'}
)

job_id = response.json()["job_id"]
print(f"Job created: {job_id}")
```

### Job 상태 확인

```python
import time

while True:
    status = requests.get(
        f"http://localhost:8000/api/v1/jobs/{job_id}",
        headers={"X-API-Key": "your-key"}
    ).json()

    print(f"Status: {status['status']}, Progress: {status['progress']:.1f}%")

    if status["status"] in ["completed", "failed"]:
        break

    time.sleep(5)
```

### 결과 다운로드

```bash
# JSON 결과
curl -H "X-API-Key: key" \
  "http://localhost:8000/api/v1/jobs/{job_id}/result" > results.json

# ZIP 다운로드
curl -H "X-API-Key: key" \
  "http://localhost:8000/api/v1/jobs/{job_id}/download" -o results.zip
```

---

## ⚠️ 에러 코드

| Code | Description                    |
| ---- | ------------------------------ |
| 401  | API 키 누락 또는 유효하지 않음 |
| 404  | Job을 찾을 수 없음             |
| 400  | 잘못된 요청 (Job 미완료 등)    |
| 422  | 요청 데이터 검증 실패          |
| 500  | 서버 내부 오류                 |

---

## 📖 API 문서

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

```bash
# 스키마 내보내기
surfscreen api export-schema -o docs/openapi.json
```
