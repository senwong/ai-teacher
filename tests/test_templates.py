from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def test_all_templates_compile():
    template_dir = Path("app/templates")
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    templates = sorted(template_dir.glob("*.html"))
    assert templates
    for path in templates:
        env.get_template(path.name)


def test_teacher_student_profile_has_no_learning_entry():
    content = Path("app/templates/student_detail.html").read_text()
    assert "开始今天的学习" not in content
    assert "/students/{{ student.id }}/sessions" not in content
    assert "查看 / 打印登录卡" in content
    assert "重置登录 PIN" in content


def test_student_home_posts_to_learn_start():
    content = Path("app/templates/student_home.html").read_text()
    assert 'action="/learn/start"' in content
    assert 'action="/student/start"' not in content


def test_login_card_distinguishes_reusable_qr_from_one_time_pin():
    content = Path("app/templates/student_created.html").read_text()
    assert "二维码" in content
    assert "长期有效" in content
    assert "{% if pin %}" in content
    assert "系统不会再次显示这个 PIN" in content
    assert "重新查看或打印登录卡不会改变学生 PIN" in content
