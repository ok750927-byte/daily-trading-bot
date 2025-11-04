import os
import pytest


RUN_GUI_LOCAL = os.environ.get("RUN_GUI_LOCAL", "0") == "1"


@pytest.mark.skipif(not RUN_GUI_LOCAL, reason="Run local GUI automation with RUN_GUI_LOCAL=1")
def test_operator_persistence_and_gui_start(qtbot):
    """A light-weight smoke automation that checks operator persistence and starts the GUI.

    This test is intended to be run locally with a display / Xvfb and pytest-qt.
    It will:
      - ensure `results/operator.txt` exists
      - import the GUI and create the main window
      - check that the operator button has text set from the persisted file
    """
    from gui_app import TradingBotGUI

    # ensure persisted file exists
    base = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(base, '..'))
    op_file = os.path.join(repo_root, 'results', 'operator.txt')
    assert os.path.exists(op_file), "operator.txt must exist for this test"

    gui = TradingBotGUI()
    qtbot.addWidget(gui)
    # show and ensure it doesn't crash
    gui.show()

    # the operator_input is a QPushButton in our GUI; ensure current text is not default
    text = gui.operator_input.text()
    assert text and text != 'Not logged in'
