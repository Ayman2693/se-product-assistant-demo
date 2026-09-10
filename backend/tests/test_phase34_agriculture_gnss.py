from app.services.requirement_parser import interpret_text

def test_agriculture_typo_is_recognized():
    r = interpret_text("I need GNSS for my argecltural project")["requirements"]
    assert r["application"] == "agriculture / precision farming"
    assert r["technologies"] == ["gnss"]

def test_precision_farming_rtk():
    r = interpret_text("RTK GNSS for precision farming")["requirements"]
    assert r["application"] == "agriculture / precision farming"
    assert r["gnss_precision"] == "cm"
