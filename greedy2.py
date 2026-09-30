// production-compare/app.js

// CSV 파싱 후 데이터 매핑 함수 수정
function parseCSVData(csvText) {
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.trim());
    
    const data = lines.slice(1).map(line => {
        const values = line.split(',').map(v => v.trim());
        return {
            category: values[headers.indexOf('Category')] || '',
            name: values[headers.indexOf('Product Name')] || '',
            modelCode: values[headers.indexOf('Model Code')] || '',
            price: parseInt((values[headers.indexOf('Price')] || '0').replace(/[^0-9]/g, ''), 10),
            rating: values[headers.indexOf('Efficiency Rating')] || '',
            monthlyCost: parseInt((values[headers.indexOf('Monthly Electricity Cost')] || '0').replace(/[^0-9]/g, ''), 10),
            capacity: values[headers.indexOf('Capacity')] || '',
            dimensions: values[headers.indexOf('Dimensions (WxHxD mm)')] || '',
            weight: parseFloat(values[headers.indexOf('Weight (kg)')] || '0')
        };
    });

    return data;
}

// 화면 테이블 / 비교 뷰 렌더링 시 매핑된 키값을 사용하도록 수정
function renderComparisonTable(products) {
    const tableBody = document.getElementById('product-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = products.map(item => `
        <tr>
            <td>${item.category}</td>
            <td><strong>${item.name}</strong></td>
            <td>${item.modelCode}</td>
            <td>${item.price.toLocaleString()}원</td>
            <td><span class="badge rating-${item.rating}">${item.rating}</span></td>
            <td>${item.monthlyCost.toLocaleString()}원</td>
            <td>${item.capacity}</td>
            <td>${item.dimensions}</td>
            <td>${item.weight}kg</td>
        </tr>
    `).join('');
}
