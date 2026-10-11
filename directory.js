const get=id=>document.getElementById(id);
const rows=[...document.querySelectorAll('.catalog-row')];
function filterSets(){
 const query=get('set-search').value.toLowerCase().trim(),sport=get('sport-filter').value,year=get('year-filter').value;
 let count=0;
 rows.forEach(row=>{row.hidden=Boolean((query&&!row.dataset.search.includes(query))||(sport&&row.dataset.sport!==sport)||(year&&row.dataset.year!==year));if(!row.hidden)count++;});
 get('catalog-count').textContent=`${count} ${count===1?'set':'sets'}`;
 get('catalog-empty').hidden=count>0;
}
get('set-search').addEventListener('input',filterSets);
['sport-filter','year-filter'].forEach(id=>get(id).addEventListener('change',filterSets));
get('catalog-reset').addEventListener('click',()=>{['set-search','sport-filter','year-filter'].forEach(id=>get(id).value='');filterSets();});
