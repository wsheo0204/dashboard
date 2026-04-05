async function loadProducts() {
  const response = await fetch('./data/products.json', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error('상품 데이터를 불러오지 못했습니다.');
  }
  return response.json();
}

function formatPrice(price) {
  return new Intl.NumberFormat('ko-KR').format(price) + '원';
}

function renderSummary(data) {
  const updatedAt = document.getElementById('updatedAt');
  const lowestPrice = document.getElementById('lowestPrice');
  const productCount = document.getElementById('productCount');

  updatedAt.textContent = data.updated_at || '-';
  productCount.textContent = String(data.products.length);

  const prices = data.products.map((p) => p.price).filter((p) => Number.isFinite(p));
  lowestPrice.textContent = prices.length ? formatPrice(Math.min(...prices)) : '-';

  const filterDetails = document.getElementById('filterDetails');
  if (filterDetails && data.filters_applied) {
    const filters = data.filters_applied;
    const chunks = [
      filters.size_inch ? `${filters.size_inch}인치` : null,
      Array.isArray(filters.resolution_tokens) ? `해상도 키워드: ${filters.resolution_tokens.join(', ')}` : null,
      Array.isArray(filters.required_ports) ? `포트: ${filters.required_ports.join(', ')}` : null,
      Array.isArray(filters.queries) ? `검색어: ${filters.queries.join(' / ')}` : null,
    ].filter(Boolean);
    filterDetails.textContent = chunks.length ? chunks.join(' · ') : '기준 정보 없음';
  }
}

function renderList(products) {
  const list = document.getElementById('list');
  const template = document.getElementById('itemTemplate');
  list.innerHTML = '';

  if (!products.length) {
    list.innerHTML = '<p class="item">조건에 맞는 상품이 없습니다.</p>';
    return;
  }

  products.forEach((product) => {
    const node = template.content.cloneNode(true);
    node.querySelector('.name').textContent = product.name;
    node.querySelector('.meta').textContent = [
      product.brand || null,
      product.size_inch ? `${product.size_inch}인치` : null,
      product.resolution || null,
      product.usb_c_pd_watt ? `USB-C PD ${product.usb_c_pd_watt}W` : 'USB-C 정보 없음',
      product.vesa_mount_mm ? `VESA ${product.vesa_mount_mm}mm` : 'VESA 정보 없음',
    ]
      .filter(Boolean)
      .join(' · ');
    node.querySelector('.price').textContent = formatPrice(product.price);
    const link = node.querySelector('.link');
    link.href = product.url;
    list.appendChild(node);
  });
}

function filterProducts(products, maxPrice) {
  if (!Number.isFinite(maxPrice) || maxPrice <= 0) return products;
  return products.filter((p) => p.price <= maxPrice);
}

(async () => {
  try {
    const data = await loadProducts();
    renderSummary(data);
    let visible = [...data.products];
    renderList(visible);

    document.getElementById('applyFilterButton').addEventListener('click', () => {
      const maxPrice = Number(document.getElementById('maxPriceInput').value);
      visible = filterProducts(data.products, maxPrice);
      renderList(visible);
    });
  } catch (error) {
    const list = document.getElementById('list');
    list.innerHTML = `<p class="item">오류: ${error.message}</p>`;
  }
})();
