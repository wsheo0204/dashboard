# 돈쓸것 Dashboard

27인치 / 4K / USB-C 충전 가능한 모니터를 다나와 검색 결과에서 필터링해서 보여주는 정적 웹 대시보드입니다.

## 동작 방식

- `scripts/fetch_danawa.py`가 다나와 검색 페이지를 수집해 `data/products.json`을 생성합니다.
- GitHub Actions가 6시간마다 데이터를 갱신합니다.
- 정적 페이지(`index.html`)는 `data/products.json`만 읽어 화면에 표시합니다.

## 배포 (GitHub Pages)

1. 이 레포를 GitHub에 push
2. Settings → Pages → Build and deployment 를 **GitHub Actions**로 선택
3. `deploy-pages` 워크플로우 실행
4. 배포 URL:
   - `https://<github-username>.github.io/<repo-name>/`

## 참고

- 다나와 페이지 구조가 변하면 스크래퍼 파싱 로직 업데이트가 필요할 수 있습니다.
- 이 저장소에는 샘플 데이터가 포함되어 있어 배포 직후에도 화면이 뜹니다.
