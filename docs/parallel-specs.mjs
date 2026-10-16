// Exact family + parallel joins only. A color is never a universal print run.
export const parallelKey=value=>String(value??'').toUpperCase().replace(/FILAGREE/g,'FILIGREE').replace(/\bPARALLEL\b/g,'').replace(/[^A-Z0-9]/g,'');
export function publishedNumbering(value){const s=String(value??'').trim();return /^\d+$/.test(s)?`/${s}`:s||'Not published';}
// Configuration, availability and a subject roster do not establish parallel
// terms. Require a populated, explicitly labelled source field or mapped limit.
export function hasParallelSpecifications(data){
 if(!data)return false;
 if(data.parallelSpecifications?.length||data.odds?.some(o=>o.numbering)||data.serialColumn!=null&&data.rows?.some(r=>r[data.serialColumn]))return true;
 return (data.publishedSpecifications??[]).some(spec=>spec.headers.some((header,i)=>/parallel|numbering|sequence|\bfoil\b|\bquantity\b|print run|^Published (?:statement|term)$/i.test(header)&&spec.rows.some(row=>String(row[i]??'').trim())));
}
// The shared view already explains family scope. Keep substantive source
// qualifiers while removing only the repeated introductory disclaimer.
export function displayQualification(value){return String(value??'').replace(/^Published for (?:this|the named) family(?: only)?; individual-card (?:parallel )?eligibility is not inferred\.\s*/,'').trim();}
export function reconcileParallels(data){
 const odds=(data.odds??[]).map(o=>({...o}));
 const sections=[...new Set((data.rows??[]).map(r=>r[0]))];
 for(const spec of data.publishedSpecifications??[]){
  // Card-specific NOW, Panini and Leaf tables must retain their card scope.
  const pi=spec.headers.findIndex(h=>/^parallel\s*\/\s*variation$/i.test(h));
  const ni=spec.headers.findIndex(h=>/^published numbering$/i.test(h));
  if(pi<0||ni<0||!sections.includes(spec.name))continue;
  for(const row of spec.rows){
   const label=String(row[pi]??'');if(!label)continue;
   const full=parallelKey(spec.name+' '+label);
   const matches=odds.filter(o=>parallelKey(o.name)===full||parallelKey(o.name)===parallelKey(label)&&parallelKey(label).startsWith(parallelKey(spec.name)));
   if(matches.length){for(const o of matches)o.numbering=publishedNumbering(row[ni]);}
   else odds.push({name:spec.name+' '+label,values:{},numbering:publishedNumbering(row[ni]),specificationOnly:true,source:row[spec.headers.findIndex(h=>/official source/i.test(h))]});
  }
 }
 for(const spec of data.parallelSpecifications??[]){
  const matching=spec.oddsName?odds.find(o=>o.name===spec.oddsName):null;
  if(matching){matching.numbering=spec.numbering;matching.numberingSource={url:spec.source,qualification:spec.qualification};matching.family=spec.family;}
  else if(!odds.some(o=>o.specificationKey===spec.family+'|'+spec.name))odds.push({name:spec.family+' '+spec.name,family:spec.family,values:{},numbering:spec.numbering,numberingSource:{url:spec.source,qualification:spec.qualification},specificationOnly:true,specificationKey:spec.family+'|'+spec.name});
 }
 return odds;
}
export function categoryNumbering(data,name){
 const odd=(data.odds??[]).find(o=>parallelKey(o.name)===parallelKey(name));if(odd?.numbering)return odd.numbering;
 if(data.serialColumn!=null){const values=[...new Set((data.rows??[]).filter(r=>parallelKey(r[0])===parallelKey(name)&&r[data.serialColumn]).map(r=>publishedNumbering(r[data.serialColumn])))];if(values.length===1)return values[0];if(values.length>1)return 'Varies by card; see official card details';}
 for(const spec of data.publishedSpecifications??[]){if(parallelKey(spec.name)!==parallelKey(name))continue;const column=spec.headers.findIndex(h=>/^Published SEQUENCE$|^Published numbering$/i.test(h));if(column<0)continue;const values=[...new Set(spec.rows.filter(r=>r[column]).map(r=>publishedNumbering(r[column])))];if(values.length===1)return values[0];if(values.length>1)return 'Varies by card; see official card details';}
 return 'Not published';
}

// Only explicitly named numbering fields are formatted. Quantity, card numbers,
// pack contents, source row numbers and unlabeled additions retain source units.
export function specificationRows(spec){return spec.rows.map(row=>row.map((value,i)=>{
 const header=String(spec.headers[i]??'');
 const serial=/^Published (?:SEQUENCE|numbering)$|^(?:Unsigned|Autograph) numbering$/i.test(header);
 const foil=spec.headers.some(h=>/^foil$/i.test(h))&&/\b(?:Silver|Platinum|Purple|Pink|Blue|Orange|Green|Red|White|Gold|Black|Bronze|Yellow)\b/i.test(header)&&!/^Quantity$|Additions/i.test(header);
 return (serial||foil)&&/^\d+$/.test(String(value??''))?publishedNumbering(value):value;
}));}
