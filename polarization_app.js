importScripts("https://cdn.jsdelivr.net/pyodide/v0.23.4/pyc/pyodide.js");

function sendPatch(patch, buffers, msg_id) {
  self.postMessage({
    type: 'patch',
    patch: patch,
    buffers: buffers
  })
}

async function startApplication() {
  console.log("Loading pyodide!");
  self.postMessage({type: 'status', msg: 'Loading pyodide'})
  self.pyodide = await loadPyodide();
  self.pyodide.globals.set("sendPatch", sendPatch);
  console.log("Loaded!");
  await self.pyodide.loadPackage("micropip");
  const env_spec = ['https://cdn.holoviz.org/panel/1.2.3/dist/wheels/bokeh-3.2.1-py3-none-any.whl', 'https://cdn.holoviz.org/panel/1.2.3/dist/wheels/panel-1.2.3-py3-none-any.whl', 'pyodide-http==0.2.1', 'numpy']
  for (const pkg of env_spec) {
    let pkg_name;
    if (pkg.endsWith('.whl')) {
      pkg_name = pkg.split('/').slice(-1)[0].split('-')[0]
    } else {
      pkg_name = pkg
    }
    self.postMessage({type: 'status', msg: `Installing ${pkg_name}`})
    try {
      await self.pyodide.runPythonAsync(`
        import micropip
        await micropip.install('${pkg}');
      `);
    } catch(e) {
      console.log(e)
      self.postMessage({
	type: 'status',
	msg: `Error while installing ${pkg_name}`
      });
    }
  }
  console.log("Packages loaded!");
  self.postMessage({type: 'status', msg: 'Executing code'})
  const code = `
  
import asyncio

from panel.io.pyodide import init_doc, write_doc

init_doc()


import numpy as np
import panel as pn

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Span

pn.extension("katex", sizing_mode="stretch_width")

# Default polarization parameters
DEFAULT_PD = 50
DEFAULT_PA = 30
DEFAULT_MU = 0.5

phi = np.linspace(0, 360, 721)


def modulation_curve(phi, pd, pa, mu):
    """Compute the normalized photoelectron angular distribution."""
    p = pd / 100.0
    return 1 + mu * p * np.cos(2 * np.deg2rad(phi - pa))


# Interactive parameter sliders
pd_slider = pn.widgets.FloatSlider(
    name="Polarization Degree (%)",
    start=0,
    end=100,
    step=1,
    value=DEFAULT_PD
)

pa_slider = pn.widgets.FloatSlider(
    name="Polarization Angle (degrees)",
    start=-90,
    end=90,
    step=1,
    value=DEFAULT_PA
)

mu_slider = pn.widgets.FloatSlider(
    name="Instrument Modulation Factor",
    start=0,
    end=1,
    step=0.01,
    value=DEFAULT_MU
)

# Initialize the modulation curve
source = ColumnDataSource(
    data={
        "phi": phi,
        "counts": modulation_curve(
            phi, DEFAULT_PD, DEFAULT_PA, DEFAULT_MU
        )
    }
)

# Configure the interactive plot
plot = figure(
    height=380,
    x_range=(0, 360),
    y_range=(0, 2.1),
    x_axis_label="Photoelectron Emission Angle (degrees)",
    y_axis_label="Normalized Counts",
    sizing_mode="stretch_width",
    toolbar_location=None
)

plot.line(
    "phi",
    "counts",
    source=source,
    line_width=3,
    color="#008C95"
)

plot.add_layout(
    Span(
        location=1,
        dimension="width",
        line_dash="dashed",
        line_color="gray",
        line_alpha=0.6
    )
)

plot.xaxis.ticker = [0, 90, 180, 270, 360]
plot.axis.axis_label_text_font_size = "12pt"
plot.axis.major_label_text_font_size = "10pt"
plot.grid.grid_line_alpha = 0.2
plot.outline_line_color = None

results = pn.pane.Markdown("")


def update(event=None):
    """Update the modulation curve and measurement summary."""
    pd = pd_slider.value
    pa = pa_slider.value
    mu = mu_slider.value

    source.data = {
        "phi": phi,
        "counts": modulation_curve(phi, pd, pa, mu)
    }

    amplitude = mu * pd / 100

    results.object = f"""
### Measurement Summary

| Quantity | Value |
|---|---:|
| Intrinsic polarization degree | {pd:.1f}% |
| Polarization angle | {pa:.1f}° |
| Instrument modulation factor | {mu:.2f} |
| Observed modulation amplitude | {100 * amplitude:.1f}% |
| Maximum normalized counts | {1 + amplitude:.2f} |
| Minimum normalized counts | {1 - amplitude:.2f} |
"""


# Register slider callbacks
for slider in [pd_slider, pa_slider, mu_slider]:
    slider.param.watch(update, "value")


reset_button = pn.widgets.Button(
    name="Reset Parameters",
    button_type="default"
)


def reset(event):
    """Restore the default polarization parameters."""
    pd_slider.value = DEFAULT_PD
    pa_slider.value = DEFAULT_PA
    mu_slider.value = DEFAULT_MU


reset_button.on_click(reset)

# Application introduction
intro = pn.pane.Markdown("""
# Explore X-ray Polarization

Investigate how the polarization properties of an astronomical source affect the distribution of photoelectron emission directions measured by an X-ray polarimeter.

Adjust the sliders to explore the relationship between polarization degree, polarization angle, and instrumental sensitivity.
""")

equation = pn.pane.LaTeX(
    r"$f(\phi)=1+\mu p\cos[2(\phi-\psi)]$",
    renderer="katex"
)

# Physical interpretation of the model parameters
explanation = pn.pane.Markdown("""
**Polarization degree (p):** The fraction of the incoming light that is linearly polarized.

**Polarization angle (ψ):** The preferred orientation of the electric field of the linearly polarized component.

**Modulation factor (μ):** The instrument's modulation amplitude for a 100% polarized source.

**Photoelectron emission angle (φ):** The reconstructed initial direction of a detected photoelectron.

The observed modulation amplitude is the product of the polarization fraction and modulation factor.

This model represents an idealized expected distribution without statistical noise.
""")

# Initialize and assemble the application
update()

app = pn.Column(
    intro,
    plot,
    pd_slider,
    pa_slider,
    mu_slider,
    reset_button,
    pn.layout.Divider(),
    equation,
    results,
    pn.layout.Divider(),
    explanation,
    max_width=900,
    margin=20
)

app.servable()


await write_doc()
  `

  try {
    const [docs_json, render_items, root_ids] = await self.pyodide.runPythonAsync(code)
    self.postMessage({
      type: 'render',
      docs_json: docs_json,
      render_items: render_items,
      root_ids: root_ids
    })
  } catch(e) {
    const traceback = `${e}`
    const tblines = traceback.split('\n')
    self.postMessage({
      type: 'status',
      msg: tblines[tblines.length-2]
    });
    throw e
  }
}

self.onmessage = async (event) => {
  const msg = event.data
  if (msg.type === 'rendered') {
    self.pyodide.runPythonAsync(`
    from panel.io.state import state
    from panel.io.pyodide import _link_docs_worker

    _link_docs_worker(state.curdoc, sendPatch, setter='js')
    `)
  } else if (msg.type === 'patch') {
    self.pyodide.globals.set('patch', msg.patch)
    self.pyodide.runPythonAsync(`
    state.curdoc.apply_json_patch(patch.to_py(), setter='js')
    `)
    self.postMessage({type: 'idle'})
  } else if (msg.type === 'location') {
    self.pyodide.globals.set('location', msg.location)
    self.pyodide.runPythonAsync(`
    import json
    from panel.io.state import state
    from panel.util import edit_readonly
    if state.location:
        loc_data = json.loads(location)
        with edit_readonly(state.location):
            state.location.param.update({
                k: v for k, v in loc_data.items() if k in state.location.param
            })
    `)
  }
}

startApplication()