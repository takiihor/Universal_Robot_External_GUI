  Current Script Structure

  1. Architecture Overview

  ┌──────────────────────────────────────────────────────────────────┐
  │                      Main Application (main.py)                   │
  │                     UI Framework: ui_mainwindow.py                │
  └────────────────────┬─────────────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
  ┌───────▼──────────┐    ┌────────▼────────────┐
  │  Sequential      │    │   Robot Controller  │
  │  Controller Page │◄───┤   robot_controller  │
  │  (UI Layer)      │    │   (Backend Layer)   │
  └───────┬──────────┘    └─────────────────────┘
          │
          │ Uses 3 Main Components:
          │
     ┌────┼────────────────┐
     │    │                │
     ▼    ▼                ▼
  ┌──────┐ ┌──────────┐ ┌──────────┐
  │Action│ │ Sequence │ │ Execution│
  │Lib   │ │ Editor   │ │ Control  │
  └──────┘ └──────────┘ └──────────┘

  2. File Hierarchy (Active Files Only)

  Main Application

  - main.py - Application entry point, creates main window
  - ui_mainwindow.py - Main window UI with page stack

  Sequential Controller System (✅ Currently Active)

  - sequential_controller_ui_page.py - Main UI page widget
    - Line 86: Uses CategorizedActionLibrary (action selection)
    - Line 25: Uses EnhancedActionParameterDialog (parameter input)
    - Line 74: Uses ExecutionHistoryPanel (history tracking)
    - Line 19: Uses ExecutionStepDelegate (visual execution states)
  - sequential_controller.py - Backend controller logic
    - Manages action sequence
    - Executes actions via robot_controller
    - Provides PyQt signals for UI updates
    - Lines 29-66: ActionType enumeration
    - Lines 260-350: Action dataclass
    - Lines 489-1298: SequentialController class

  UI Components

  - categorized_action_library_improved.py ✅ [ACTIVE]
    - Card-based action library UI
    - Single column layout (line 410)
    - Compact design (70-90px card height)
    - Organized by categories (movement, force, I/O, etc.)
  - sequential_controller_dialog_enhanced.py ✅ [ACTIVE]
    - Enhanced parameter dialogs
    - Preset buttons for common values
    - Help text and validation
  - execution_history_panel.py
    - Execution history table with timing
    - Step-by-step log of completed actions
  - execution_step_delegate.py
    - Custom item delegate for visual execution states
    - Shows running/success/failed indicators

  Inactive/Legacy Files (❌ Not Used)

  - sequential_controller_ui.py - Old Chinese interface (replaced)
  - sequential_controller_dialog.py - Old basic dialogs (replaced)

  Backend & Support

  - robot_controller.py - Robot RTDE communication layer
  - config.py - Configuration and preset positions
  - safety_monitor.py - Safety monitoring
  - data_logger.py - Data logging
  - error_handler.py - Error handling utilities
  - hand_guiding_tool.py - Hand guiding/freedrive tools

  3. Component Relationships

  sequential_controller_ui_page.py (Main UI)
      │
      ├─► CategorizedActionLibrary (categorized_action_library_improved.py)
      │       │
      │       └─► Emits: action_selected signal
      │           └─► Creates: ActionCard widgets
      │
      ├─► EnhancedActionParameterDialog (sequential_controller_dialog_enhanced.py)
      │       │
      │       └─► Shows parameter input forms with presets
      │
      ├─► SequentialController (sequential_controller.py)
      │       │
      │       ├─► Manages: action_sequence (List[Action])
      │       ├─► Uses: robot_controller for execution
      │       ├─► Emits: execution signals (started, progress, completed)
      │       └─► ExecutionThread: runs actions asynchronously
      │
      ├─► ExecutionHistoryPanel (execution_history_panel.py)
      │       │
      │       └─► Displays: completed actions with timing
      │
      └─► ExecutionStepDelegate (execution_step_delegate.py)
              │
              └─► Renders: visual execution states (running/success/failed)

  4. Signal Flow

  User Interaction Flow:
  1. User clicks ActionCard in CategorizedActionLibrary
     └─► action_selected(ActionType) signal emitted
         └─► sequential_controller_ui_page.on_action_card_clicked()
             └─► Opens EnhancedActionParameterDialog
                 └─► User enters parameters
                     └─► SequentialController.add_action()
                         └─► sequence_changed signal emitted
                             └─► UI updates sequence list

  Execution Flow:
  1. User clicks "Execute Task" button
     └─► SequentialController.execute_sequence()
         └─► Creates ExecutionThread
             └─► Thread emits signals:
                 ├─► execution_started(total_steps)
                 ├─► execution_step_started(index, description)
                 ├─► execution_step_completed_with_timing(...)
                 └─► execution_completed(success)
                     └─► UI updates:
                         ├─► Progress bar
                         ├─► Step highlights (ExecutionStepDelegate)
                         └─► History panel entries

  5. Data Flow

  Action Definition:
  ActionType (Enum) → ACTION_METADATA (dict) → ActionCard (UI)
                                              → Action (dataclass)
                                              → SequentialController

  Execution Path:
  SequentialController.execute_sequence()
      ├─► ExecutionThread.run()
      │       ├─► For each Action in action_sequence:
      │       │       ├─► _execute_action(action)
      │       │       │       └─► robot_controller.move_to_preset()
      │       │       │           robot_controller.move_tcp()
      │       │       │           robot_controller.enable_freedrive()
      │       │       │           etc.
      │       │       └─► Emit signals (step_started, step_completed)
      │       └─► Emit execution_completed
      └─► UI updates via signal/slot connections

  6. Key Design Patterns

  - Page Widget Pattern: UI embedded as page, not dialog
  - Signal/Slot Pattern: PyQt signals for loose coupling between UI and backend
  - Card-Based UI: Action library uses clickable cards organized by category
  - Asynchronous Execution: Actions execute in separate thread (ExecutionThread)
  - Delegate Pattern: Custom rendering for execution states (ExecutionStepDelegate)
  - Dataclass Pattern: Action represented as Python dataclass with serialization

  7. File Dependencies (Imports)

  main.py
      └─► ui_mainwindow.py
          └─► sequential_controller_ui_page.py
              ├─► categorized_action_library_improved.py
              │       └─► sequential_controller.py (ActionType, ACTION_METADATA)
              ├─► sequential_controller_dialog_enhanced.py
              │       └─► sequential_controller.py (ActionType)
              ├─► sequential_controller.py
              │       ├─► robot_controller.py
              │       └─► config.py
              ├─► execution_history_panel.py
              └─► execution_step_delegate.py

  This structure shows a clean separation between:
  - UI Layer: Page widget with categorized action library and parameter dialogs
  - Controller Layer: Sequential controller managing action sequences
  - Backend Layer: Robot controller handling RTDE communication

  The current compact design uses a single-column action library (line 410 in
  categorized_action_library_improved.py:410) with 70-90px card heights (lines 51-52).
