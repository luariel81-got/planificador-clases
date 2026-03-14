import streamlit as st
import subprocess, json, os, requests
from datetime import date
import pytz
from datetime import datetime as _dt

def hoy_py():
    return _dt.now(pytz.timezone("America/Asuncion")).date()

GRADOS = [
    "7 Grado", "8 Grado", "9 Grado",
    "1 BTS", "1 BC", "2 BC", "3 BC",
    "1 BTI", "2 BTI", "3 BTI",
]

st.set_page_config(page_title="Planificador de Clases", page_icon="📚", layout="wide")

st.markdown("""
<style>
.main .block-container { max-width: 900px; padding-top: 1.5rem; }
.stTextArea textarea { font-size: 15px !important; }
.stTextInput input  { font-size: 15px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;padding:20px 0 10px 0;">
  <div style="font-size:48px;">📚</div>
  <div style="font-size:28px;font-weight:700;margin-top:6px;">Planificador de Clases</div>
  <div style="font-size:14px;opacity:0.6;margin-top:4px;">Educacion Cristiana — MEC Paraguay</div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Datos base ────────────────────────────────────────────────────────────────
st.subheader("1️⃣  Datos de la clase")

c1, c2, c3 = st.columns([2, 2, 1])
materia  = c1.text_input("Materia", value="Educacion Cristiana")
grado    = c2.selectbox("Grado", GRADOS)
fecha    = c3.date_input("Fecha", value=hoy_py())

c4, c5 = st.columns(2)
docente  = c4.text_input("Docente", placeholder="Tu nombre completo")
duracion = c5.text_input("Duracion", value="80 minutos")

tema      = st.text_input("📖 Tema de la clase", placeholder="ej: El fruto del Espiritu - Amor")
versiculo = st.text_input("✝️ Versiculo base",   placeholder="ej: Galatas 5:22-23")

st.divider()

# ── Botón IA ──────────────────────────────────────────────────────────────────
st.subheader("2️⃣  Generar con IA")
st.caption("Ingresa el tema y versiculo arriba, luego toca el boton. Podras editar todo antes de descargar.")

if st.button("✨ Generar plan con IA", type="primary", use_container_width=True):
    if not tema.strip():
        st.error("Ingresa el tema primero.")
        st.stop()

    prompt = f"""Eres un docente experto en Educacion Cristiana para nivel secundario en Paraguay.
Genera un plan de clase completo en español para los siguientes datos:

- Materia: {materia}
- Grado: {grado}
- Tema: {tema}
- Versiculo base: {versiculo or "no especificado"}
- Duracion total: {duracion}

Responde SOLO con un JSON valido con esta estructura exacta, sin texto adicional, sin markdown:
{{
  "objetivo": "objetivo de aprendizaje claro y medible",
  "inicio": {{
    "tiempo": "15 min",
    "descripcion": "descripcion detallada de actividades de inicio"
  }},
  "desarrollo": {{
    "tiempo": "50 min",
    "descripcion": "descripcion detallada de actividades de desarrollo"
  }},
  "cierre": {{
    "tiempo": "15 min",
    "descripcion": "descripcion detallada de actividades de cierre"
  }},
  "recursos": "lista de recursos necesarios separados por coma",
  "evaluacion": "descripcion de la tarea o evaluacion"
}}"""

    with st.spinner("Generando plan de clase..."):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": st.secrets["ANTHROPIC_API_KEY"],
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1500,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            raw = resp.json()["content"][0]["text"].strip()
            # Limpiar posibles bloques markdown
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            plan = json.loads(raw)
            st.session_state["plan_ia"] = plan
            st.success("Plan generado. Revisa y edita los campos abajo antes de descargar.")
        except Exception as e:
            st.error(f"Error al generar: {e}")

st.divider()

# ── Campos editables (pre-rellenados si hay plan IA) ─────────────────────────
plan = st.session_state.get("plan_ia", {})

st.subheader("3️⃣  Revisa y edita el plan")

objetivo = st.text_area(
    "🎯 Objetivo de la clase",
    value=plan.get("objetivo", ""),
    placeholder="Al finalizar la clase, el alumno sera capaz de...",
    height=90,
)

st.markdown("**🗓️ Actividades**")
tiempos_def = {"Inicio": "15 min", "Desarrollo": "50 min", "Cierre": "15 min"}
actividades = {}
for momento, key in [("Inicio","inicio"), ("Desarrollo","desarrollo"), ("Cierre","cierre")]:
    with st.expander(f"{momento}", expanded=True):
        ca, cb = st.columns([1, 4])
        t_default = plan.get(key, {}).get("tiempo", tiempos_def[momento])
        d_default = plan.get(key, {}).get("descripcion", "")
        t    = ca.text_input("Tiempo", value=t_default, key=f"t_{momento}")
        desc = cb.text_area("Actividades", value=d_default,
                            placeholder=f"Actividades del {momento.lower()}...",
                            key=f"a_{momento}", height=100)
        actividades[momento] = {"tiempo": t, "descripcion": desc}

cr, ce = st.columns(2)
with cr:
    st.markdown("**🛠️ Recursos**")
    recursos = st.text_area("Lista", value=plan.get("recursos",""),
                             placeholder="Biblia, pizarron, fichas...", height=100)
with ce:
    st.markdown("**📝 Tarea / Evaluacion**")
    evaluacion = st.text_area("Descripcion", value=plan.get("evaluacion",""),
                               placeholder="Tarea o evaluacion...", height=100)

observaciones = st.text_area("💬 Observaciones (opcional)", height=70)

st.divider()

# ── Generar Word ──────────────────────────────────────────────────────────────
st.subheader("4️⃣  Descargar")

if st.button("📥 Generar y descargar Word (.docx)", type="primary", use_container_width=True):
    if not tema.strip():
        st.error("Ingresa el tema primero.")
        st.stop()

    data = {
        "materia": materia, "grado": grado,
        "fecha": fecha.strftime("%d/%m/%Y"),
        "docente": docente or "---", "duracion": duracion,
        "tema": tema, "versiculo": versiculo,
        "objetivo": objetivo or "---",
        "actividades": actividades,
        "recursos": recursos or "---",
        "evaluacion": evaluacion or "---",
        "observaciones": observaciones or "",
    }

    data_path = "/tmp/plan_data.json"
    js_path   = "/tmp/gen_plan.js"
    out_path  = "/tmp/plan_clase.docx"

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    js_code = """const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, BorderStyle, WidthType, ShadingType, VerticalAlign } = require('docx');
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('DATA_PATH','utf8'));
const BLUE='1F4E79',LBLUE='D6E4F0',LBLUE2='EBF4FA',WHITE='FFFFFF',DARK='1A1A2E';
const br={style:BorderStyle.SINGLE,size:1,color:'B0C4D8'};
const borders={top:br,bottom:br,left:br,right:br};
function hdr(t){return new Paragraph({children:[new TextRun({text:t,bold:true,size:26,color:WHITE,font:'Arial'})],
  shading:{fill:BLUE,type:ShadingType.CLEAR},spacing:{before:160,after:80},indent:{left:120,right:120}});}
function lbl(t){return new TextRun({text:t,bold:true,size:22,color:BLUE,font:'Arial'});}
function val(t){return new TextRun({text:' '+(t||'---'),size:22,color:DARK,font:'Arial'});}
function ic(l,v,bg){return new TableCell({borders,width:{size:4680,type:WidthType.DXA},
  shading:{fill:bg,type:ShadingType.CLEAR},margins:{top:80,bottom:80,left:120,right:120},
  children:[new Paragraph({children:[lbl(l),val(v)]})]});}
function actRow(m,ti,de){return new TableRow({children:[
  new TableCell({borders,width:{size:1500,type:WidthType.DXA},shading:{fill:LBLUE,type:ShadingType.CLEAR},
    margins:{top:80,bottom:80,left:120,right:120},verticalAlign:VerticalAlign.TOP,
    children:[new Paragraph({children:[new TextRun({text:m,bold:true,size:22,color:BLUE,font:'Arial'})]}),
              new Paragraph({children:[new TextRun({text:ti,size:20,color:'666666',font:'Arial'})]})]}),
  new TableCell({borders,width:{size:7860,type:WidthType.DXA},shading:{fill:WHITE,type:ShadingType.CLEAR},
    margins:{top:80,bottom:80,left:120,right:120},
    children:[new Paragraph({children:[new TextRun({text:de||'---',size:22,color:DARK,font:'Arial'})]})]}),
]});}
const ch=[
  new Paragraph({children:[new TextRun({text:'PLAN DE CLASE',bold:true,size:40,color:BLUE,font:'Arial'})],
    alignment:AlignmentType.CENTER,spacing:{before:0,after:80},
    border:{bottom:{style:BorderStyle.SINGLE,size:6,color:BLUE,space:4}}}),
  new Paragraph({children:[new TextRun({text:data.tema,bold:true,size:30,color:'2E75B6',font:'Arial'})],
    alignment:AlignmentType.CENTER,spacing:{before:60,after:40}}),
  new Paragraph({children:[new TextRun({text:data.versiculo?'   '+data.versiculo:'',italics:true,size:22,color:'555555',font:'Arial'})],
    alignment:AlignmentType.CENTER,spacing:{before:0,after:200}}),
  hdr('INFORMACION GENERAL'),
  new Table({width:{size:9360,type:WidthType.DXA},columnWidths:[4680,4680],rows:[
    new TableRow({children:[ic('Materia:',data.materia,LBLUE2),ic('Curso:',data.grado,WHITE)]}),
    new TableRow({children:[ic('Docente:',data.docente,LBLUE2),ic('Fecha:',data.fecha,WHITE)]}),
    new TableRow({children:[ic('Duracion:',data.duracion,LBLUE2),ic('','',WHITE)]}),
  ]}),
  hdr('OBJETIVO DE LA CLASE'),
  new Paragraph({children:[new TextRun({text:data.objetivo,size:22,color:DARK,font:'Arial'})],
    spacing:{before:80,after:80},indent:{left:200},
    border:{left:{style:BorderStyle.SINGLE,size:12,color:'2E75B6',space:8}}}),
  hdr('DESARROLLO DE LA CLASE'),
  new Table({width:{size:9360,type:WidthType.DXA},columnWidths:[1500,7860],rows:[
    new TableRow({children:[
      new TableCell({borders,width:{size:1500,type:WidthType.DXA},shading:{fill:BLUE,type:ShadingType.CLEAR},
        margins:{top:80,bottom:80,left:120,right:120},
        children:[new Paragraph({children:[new TextRun({text:'Momento',bold:true,size:22,color:WHITE,font:'Arial'})]})]}),
      new TableCell({borders,width:{size:7860,type:WidthType.DXA},shading:{fill:BLUE,type:ShadingType.CLEAR},
        margins:{top:80,bottom:80,left:120,right:120},
        children:[new Paragraph({children:[new TextRun({text:'Actividades',bold:true,size:22,color:WHITE,font:'Arial'})]})]}),
    ]}),
    actRow('Inicio',data.actividades.Inicio.tiempo,data.actividades.Inicio.descripcion),
    actRow('Desarrollo',data.actividades.Desarrollo.tiempo,data.actividades.Desarrollo.descripcion),
    actRow('Cierre',data.actividades.Cierre.tiempo,data.actividades.Cierre.descripcion),
  ]}),
  hdr('RECURSOS Y EVALUACION'),
  new Table({width:{size:9360,type:WidthType.DXA},columnWidths:[4680,4680],rows:[
    new TableRow({children:[
      new TableCell({borders,width:{size:4680,type:WidthType.DXA},shading:{fill:LBLUE,type:ShadingType.CLEAR},
        margins:{top:80,bottom:80,left:120,right:120},children:[
          new Paragraph({children:[new TextRun({text:'Recursos y materiales',bold:true,size:22,color:BLUE,font:'Arial'})]}),
          new Paragraph({children:[new TextRun({text:data.recursos,size:22,color:DARK,font:'Arial'})]})]}),
      new TableCell({borders,width:{size:4680,type:WidthType.DXA},shading:{fill:WHITE,type:ShadingType.CLEAR},
        margins:{top:80,bottom:80,left:120,right:120},children:[
          new Paragraph({children:[new TextRun({text:'Tarea / Evaluacion',bold:true,size:22,color:BLUE,font:'Arial'})]}),
          new Paragraph({children:[new TextRun({text:data.evaluacion,size:22,color:DARK,font:'Arial'})]})]}),
    ]})
  ]),
];
if(data.observaciones){
  ch.push(hdr('OBSERVACIONES'));
  ch.push(new Paragraph({children:[new TextRun({text:data.observaciones,size:22,color:DARK,font:'Arial',italics:true})],
    spacing:{before:80,after:80},indent:{left:200}}));
}
ch.push(new Paragraph({children:[],spacing:{before:400}}));
ch.push(new Paragraph({children:[new TextRun({text:'_'.repeat(40),color:'999999',size:22,font:'Arial'})],alignment:AlignmentType.CENTER}));
ch.push(new Paragraph({children:[new TextRun({text:data.docente,bold:true,size:22,color:BLUE,font:'Arial'})],alignment:AlignmentType.CENTER}));
ch.push(new Paragraph({children:[new TextRun({text:'Docente - '+data.materia,size:20,color:'666666',font:'Arial'})],alignment:AlignmentType.CENTER}));
const doc=new Document({sections:[{properties:{page:{size:{width:12240,height:15840},
  margin:{top:1008,right:1008,bottom:1008,left:1008}}},children:ch}]});
Packer.toBuffer(doc).then(buf=>{
  fs.writeFileSync('OUT_PATH',buf);
  console.log('OK');
}).catch(e=>{console.error(e);process.exit(1);});
""".replace("DATA_PATH", data_path).replace("OUT_PATH", out_path)

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_code)

    npm_root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    env = os.environ.copy()
    env["NODE_PATH"] = npm_root

    result = subprocess.run(["node", js_path], capture_output=True, text=True, env=env)

    if result.returncode != 0 or not os.path.exists(out_path):
        st.error(f"Error al generar el documento: {result.stderr}")
    else:
        with open(out_path, "rb") as f:
            docx_bytes = f.read()
        nombre = f"plan_{grado.replace(' ','_')}_{fecha.strftime('%d%m%Y')}.docx"
        st.download_button(
            "⬇️ Descargar plan de clase",
            data=docx_bytes,
            file_name=nombre,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        st.success(f"Listo — {tema} — {grado} — {fecha.strftime('%d/%m/%Y')}")
