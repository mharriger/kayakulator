## Plan: Tree Visibility Checkboxes

TL;DR: Add tree-based visibility checkboxes so each stringer can show/hide `Offsets`, `Curve`, and `Solid` individually, and allow a master checkbox to toggle all three at once.

1. Update `src/gui/kayakulator_document_tree_model.py`.
   - [x] Make each stringer child item checkable.
   - [x] Add `Offsets`, `Curve`, and `Solid` checkbox items under each stringer.
   - [x] Make top-level stringer nodes checkable and support tri-state behavior.

2. Encode metadata on tree items.
   - [x] Store the `Member` value on stringer items using `Qt.UserRole`.
   - [x] Store the visibility category string (`offsets`, `curve`, `solid`) on subitems using another role.

3. Extend document shape tracking in `src/kayakulator_document.py`.
   - [x] Change `member_shapes` from `dict[Member, AIS_Shape]` to category-aware storage.
   - [x] Use a structure like `dict[Member, dict[str, list[AIS_Shape]]]` to keep separate lists for `offsets`, `curve`, and `solid`.

4. Update `src/gui/mainwindow.py` display behavior.
   - [x] Populate the new categorized shape registry when the model is displayed.
   - [x] Keep existing `solid` shape display behavior and plan for `offsets` / `curve` categories.
   - [x] Add methods to show/hide a single member/category and to toggle all categories for one member.

5. Connect tree checkbox changes to visibility updates.
   - [x] Attach an `itemChanged` handler in `src/gui/document_tree_widget.py` or `MainWindow`.
   - [x] The handler should read the member and category metadata and call the display visibility helper.

6. Ensure parent-child checkbox syncing.
   - [x] When a parent stringer checkbox is changed, apply the state to all child categories.
   - [x] When a child category checkbox is changed, update the parent tri-state.

7. Preserve default visibility on refresh.
   - [x] New tree items should default to checked.
   - [x] `refresh()` should rebuild the tree with all categories visible unless state was explicitly changed.

8. Verify the feature.
   - [ ] Open an offsets file, confirm the tree shows `Offsets`, `Curve`, and `Solid` checkboxes.
   - [ ] Toggle a subitem and verify the corresponding category hides/shows in the 3D display.
   - [ ] Toggle a top-level stringer checkbox and verify all subcategories update.

**Files to modify**
- `src/gui/kayakulator_document_tree_model.py`
- `src/gui/document_tree_widget.py`
- `src/kayakulator_document.py`
- `src/gui/mainwindow.py`
