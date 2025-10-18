async function fetchData() {
    const res = await fetch('/api/data');
    const json = await res.json();
    if (!json.ok) throw new Error(json.error || 'Error al cargar datos');
    return json.rows;
}

function drawTable(rows) {
    const table = document.getElementById('dataTable');
    table.innerHTML = '';
    if (!rows.length) { table.innerHTML = '<tr><td>Sin datos</td></tr>'; return; }


    const headers = Object.keys(rows[0]);
    const thead = document.createElement('thead');
    const trh = document.createElement('tr');
    headers.forEach(h => {
        const th = document.createElement('th');
        th.textContent = h;
        trh.appendChild(th);
    });
    thead.appendChild(trh);


    const tbody = document.createElement('tbody');
    rows.forEach(r => {
        const tr = document.createElement('tr');
        headers.forEach(h => {
            const td = document.createElement('td');
            td.textContent = r[h] ?? '';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });


    table.appendChild(thead);
    table.appendChild(tbody);
}

function drawAddForm(headers) {
    const form = document.getElementById('addForm');
    form.innerHTML = '';
    headers.forEach(h => {
        const wrapper = document.createElement('div');
        const label = document.createElement('label');
        label.textContent = h;
        const input = document.createElement('input');
        input.name = h;
        input.placeholder = `Valor para ${h}`;
        wrapper.appendChild(label);
        wrapper.appendChild(input);
        form.appendChild(wrapper);
    });
    document.getElementById('columnsHelp').textContent = `Columnas detectadas: ${headers.join(', ')}`;
}

async function init() {
    try {
        const rows = await fetchData();
        drawTable(rows);
        const headers = rows.length ? Object.keys(rows[0]) : [];
        if (headers.length) drawAddForm(headers);


        document.getElementById('addBtn').addEventListener('click', async () => {
            const formEl = document.getElementById('addForm');
            const payload = {};
            [...formEl.elements].forEach(el => { if (el.name) payload[el.name] = el.value; });
            const res = await fetch('/api/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const json = await res.json();
            const msg = document.getElementById('addMsg');
            if (json.ok) {
                msg.textContent = 'Fila agregada correctamente';
                const newRows = await fetchData();
                drawTable(newRows);
                // Limpia inputs
                [...formEl.elements].forEach(el => { if (el.name) el.value = ''; });
            } else {
                msg.textContent = 'Error: ' + (json.error || 'No se pudo agregar');
            }
        });
    } catch (e) {
        console.error(e);
        document.body.insertAdjacentHTML('beforeend', `<p style="color:#b91c1c">${e.message}</p>`);
    }
}

init();