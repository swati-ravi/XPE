import numpy as np

from pathlib import Path
from bokeh.plotting import figure, save, output_file
from bokeh.models import ColumnDataSource, Slider, Button, Div, CustomJS, Span
from bokeh.layouts import column
from bokeh.resources import INLINE
from bokeh.io import curdoc
from bokeh.core.templates import FILE

curdoc().theme = "dark_minimal"

# Default polarization parameters
DEFAULT_PD = 50
DEFAULT_PA = 30
DEFAULT_MU = 0.5

phi = np.linspace(0, 360, 721)


def modulation_curve(phi, pd, pa, mu):
    """Compute the normalized photoelectron angular distribution."""
    return 1 + mu * pd / 100 * np.cos(2 * np.deg2rad(phi - pa))


def measurement_summary(pd, pa, mu):
    """Generate the polarization measurement summary."""
    amplitude = mu * pd / 100

    return f"""
    <h3>Measurement Summary</h3>
    <table style="width:100%; border-collapse:collapse; line-height:2;">
        <tr><td>Intrinsic polarization degree</td><td>{pd:.1f}%</td></tr>
        <tr><td>Polarization angle</td><td>{pa:.1f}°</td></tr>
        <tr><td>Instrument modulation factor</td><td>{mu:.2f}</td></tr>
        <tr><td>Observed modulation amplitude</td><td>{100 * amplitude:.1f}%</td></tr>
        <tr><td>Maximum normalized counts</td><td>{1 + amplitude:.2f}</td></tr>
        <tr><td>Minimum normalized counts</td><td>{1 - amplitude:.2f}</td></tr>
    </table>
    """


# Application introduction
intro = Div(text="""
<h1>Explore X-ray Polarization</h1>

<p>Investigate how the polarization properties of an astronomical
source affect the distribution of photoelectron emission directions
measured by an X-ray polarimeter.</p>

<p>Adjust the sliders to explore the relationship between polarization
degree, polarization angle, and instrumental sensitivity.</p>
""", sizing_mode="stretch_width")

# Initialize the modulation curve
source = ColumnDataSource(data={
    "phi": phi,
    "counts": modulation_curve(phi, DEFAULT_PD, DEFAULT_PA, DEFAULT_MU)
})

plot = figure(
    aspect_ratio=2.5,
    min_height=280,
    max_height=650,
    x_range=(0, 360),
    y_range=(0, 2.1),
    x_axis_label="Photoelectron Emission Angle (degrees)",
    y_axis_label="Normalized Counts",
    sizing_mode="scale_width",
    toolbar_location=None
)

plot.line(
    "phi",
    "counts",
    source=source,
    line_width=3,
    color="#14B8A6"
)

plot.add_layout(Span(
    location=1,
    dimension="width",
    line_dash="dashed",
    line_color="gray",
    line_alpha=0.6
))

# Plot styling
plot.xaxis.ticker = [0, 90, 180, 270, 360]
plot.axis.axis_label_text_font_size = "12pt"
plot.axis.major_label_text_font_size = "10pt"

# Dark plot styling
plot.background_fill_color = "#18181b"
plot.border_fill_color = "#18181b"
plot.outline_line_color = None

plot.axis.axis_label_text_color = "#e4e4e7"
plot.axis.major_label_text_color = "#e4e4e7"
plot.axis.axis_line_color = "#a1a1aa"
plot.axis.major_tick_line_color = "#a1a1aa"
plot.axis.minor_tick_line_color = "#71717a"

plot.grid.grid_line_color = "#52525b"
plot.grid.grid_line_alpha = 0.35

# Interactive parameter sliders
pd_slider = Slider(
    title="Polarization Degree (%)",
    start=0,
    end=100,
    step=1,
    value=DEFAULT_PD,
    sizing_mode="stretch_width"
)

pa_slider = Slider(
    title="Polarization Angle (degrees)",
    start=-90,
    end=90,
    step=1,
    value=DEFAULT_PA,
    sizing_mode="stretch_width"
)

mu_slider = Slider(
    title="Instrument Modulation Factor",
    start=0,
    end=1,
    step=0.01,
    value=DEFAULT_MU,
    sizing_mode="stretch_width"
)

results = Div(
    text=measurement_summary(DEFAULT_PD, DEFAULT_PA, DEFAULT_MU),
    sizing_mode="stretch_width"
)

# Update the curve and summary in the browser
callback = CustomJS(
    args=dict(
        source=source,
        pd_slider=pd_slider,
        pa_slider=pa_slider,
        mu_slider=mu_slider,
        results=results
    ),
    code="""
    const pd = pd_slider.value;
    const pa = pa_slider.value;
    const mu = mu_slider.value;
    const amplitude = mu * pd / 100;

    const phi = source.data.phi;
    const counts = source.data.counts;

    for (let i = 0; i < phi.length; i++) {
        counts[i] = 1 + amplitude *
            Math.cos(2 * (phi[i] - pa) * Math.PI / 180);
    }

    source.change.emit();

    results.text = `
        <h3>Measurement Summary</h3>
        <table style="width:100%; border-collapse:collapse; line-height:2;">
            <tr>
                <td>Intrinsic polarization degree</td>
                <td>${pd.toFixed(1)}%</td>
            </tr>
            <tr>
                <td>Polarization angle</td>
                <td>${pa.toFixed(1)}°</td>
            </tr>
            <tr>
                <td>Instrument modulation factor</td>
                <td>${mu.toFixed(2)}</td>
            </tr>
            <tr>
                <td>Observed modulation amplitude</td>
                <td>${(100 * amplitude).toFixed(1)}%</td>
            </tr>
            <tr>
                <td>Maximum normalized counts</td>
                <td>${(1 + amplitude).toFixed(2)}</td>
            </tr>
            <tr>
                <td>Minimum normalized counts</td>
                <td>${(1 - amplitude).toFixed(2)}</td>
            </tr>
        </table>
    `;
    """
)

for slider in [pd_slider, pa_slider, mu_slider]:
    slider.js_on_change("value", callback)

# Restore the default parameters
reset_button = Button(
    label="Reset Parameters",
    button_type="default",
    width=180
)

reset_button.js_on_click(CustomJS(
    args=dict(
        pd_slider=pd_slider,
        pa_slider=pa_slider,
        mu_slider=mu_slider,
        default_pd=DEFAULT_PD,
        default_pa=DEFAULT_PA,
        default_mu=DEFAULT_MU
    ),
    code="""
    pd_slider.value = default_pd;
    pa_slider.value = default_pa;
    mu_slider.value = default_mu;
    """
))

# Display the modulation equation
equation = Div(text="""
<hr>
<div style="text-align:center; font-size:24px;
            font-family:Georgia,serif; padding:15px;">
    <i>f</i>(φ) = 1 + μ<i>p</i> cos[2(φ − ψ)]
</div>
""", sizing_mode="stretch_width")

# Physical interpretation of the model parameters
explanation = Div(text="""
<hr>

<h3>Understanding the Parameters</h3>

<p><b>Polarization degree (p):</b> The fraction of the incoming light that is linearly polarized.</p>

<p><b>Polarization angle (ψ):</b> The preferred orientation of the electric field of the linearly polarized component.</p>

<p><b>Modulation factor (μ):</b> The instrument's modulation amplitude for a 100% polarized source.</p>

<p><b>Photoelectron emission angle (φ):</b> The reconstructed initial direction of a detected photoelectron.</p>

<p>The observed modulation amplitude is the product of the polarization fraction and modulation factor.</p>

<p><i>This model represents an idealized expected distribution without statistical noise.</i></p>
""", sizing_mode="stretch_width")

# Assemble the application
# Assemble the application
app = column(
    intro,
    plot,
    pd_slider,
    pa_slider,
    mu_slider,
    reset_button,
    equation,
    results,
    explanation,
    sizing_mode="stretch_width",
    margin=20
)

# Apply permanent dark styling
template = FILE.environment.from_string("""
{% extends base %}

{% block preamble %}
<style>
    html, body {
        background-color: #18181b;
        color: #e4e4e7;
        color-scheme: dark;
        margin: 0;
        font-family: Arial, sans-serif;
    }

    hr {
        border: none;
        border-top: 1px solid #52525b;
    }
</style>
{% endblock %}
""")

# Export the standalone application
output_path = Path(__file__).resolve().with_name(
    "polarization_app.html"
)

output_file(
    str(output_path),
    title="Interactive X-ray Polarization Explorer"
)

save(app, resources=INLINE, template=template)

print(f"Application saved to {output_path}")
