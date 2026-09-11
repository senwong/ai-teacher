from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def test_all_templates_compile():
    template_dir = Path("app/templates")
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    templates = sorted(template_dir.glob("*.html"))
    assert templates
    for path in templates:
        env.get_template(path.name)
