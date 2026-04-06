# 돈쓸것 Dashboard

27인치 / 4K / USB-C 충전 가능한 모니터를 다나와 검색 결과에서 필터링해서 보여주는 정적 웹 대시보드입니다.
기본 검색어 외에 삼성/LG 검색어도 함께 수집하며, 각 상품 상세 페이지까지 조회해 USB-C PD(W), VESA 마운트, 상품 이미지를 표시합니다.

## 동작 방식

- `scripts/fetch_danawa.py`가 다나와 검색 페이지를 수집한 뒤, 각 상품 상세 페이지를 추가 조회해 `data/products.json`을 생성합니다.
  - 상세 페이지 스펙 기반 보강: **PD(W) / VESA / 이미지**를 우선적으로 상세 스펙 영역에서 파싱합니다.
  - PD 파싱 우선순위:
    1. 구조화된 스펙/테이블
    2. 명시적 키워드 문맥(USB-C PD, Power Delivery, 충전 출력)
    3. 일반 본문 텍스트 fallback
  - 신뢰도 낮은 값(소비전력/어댑터 출력으로 보이는 값)은 버리고 `null` 유지 정책을 사용합니다.
  - 이미지 파싱 우선순위:
    1. `og:image`
    2. `twitter:image`
    3. 본문 대표 이미지(`prod_img`, `big_img` 등)
  - `//...` 형태의 protocol-relative 이미지 URL은 `https://...`로 정규화합니다.
- 상세 페이지 fetch/파싱이 실패해도 전체 수집은 중단하지 않고, 해당 상품만 fallback(`PD/VESA/이미지 = null`) 처리합니다.
- 동일 상세 URL은 실행 중 캐시하여 중복 fetch를 방지합니다.
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
