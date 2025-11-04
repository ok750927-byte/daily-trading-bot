import os
import tempfile
import shutil


def test_merge_temp_mei_logs_creates_and_appends(tmp_path, monkeypatch):
    # create a fake _MEI dir structure in a tempdir
    fake_temp = tmp_path / "tempdir"
    fake_temp.mkdir()
    mei_name = "_MEI_FAKE123"
    mei_dir = fake_temp / mei_name
    (mei_dir / "results").mkdir(parents=True)
    temp_log = mei_dir / "results" / "gui_runtime.log"
    temp_log.write_text("LINE_FROM_MEI\n", encoding="utf-8")

    # ensure project results file exists and has initial content
    project_results = tmp_path / "project_results"
    project_results.mkdir()
    # The module writes into workspace_root/results/gui_runtime.log
    results_dir = project_results / 'results'
    results_dir.mkdir()
    proj_log = results_dir / "gui_runtime.log"
    proj_log.write_text("INITIAL\n", encoding="utf-8")

    # monkeypatch tempfile.gettempdir to return our fake tempdir
    monkeypatch.setattr('tempfile.gettempdir', lambda: str(fake_temp))

    # monkeypatch env so module-level workspace detection picks it up on import
    monkeypatch.setenv('DAILY_TRADING_WORKSPACE', str(project_results))

    # import the module after env is set so it computes log_path correctly
    import importlib
    import gui_app_recovered
    importlib.reload(gui_app_recovered)

    # call merge
    gui_app_recovered.merge_temp_mei_logs()

    # assert that proj_log now contains both INITIAL and LINE_FROM_MEI
    content = proj_log.read_text(encoding='utf-8')
    assert "INITIAL" in content
    assert "LINE_FROM_MEI" in content

    # cleanup - not strictly necessary as tmp_path is isolated
    shutil.rmtree(str(fake_temp))
