import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export type EditorState = {
  activeDocumentId: string | null;
  selectedVersionId: string | null;
};

const initialState: EditorState = {
  activeDocumentId: null,
  selectedVersionId: null,
};

const editorSlice = createSlice({
  name: "editor",
  initialState,
  reducers: {
    setActiveDocumentId(state, action: PayloadAction<string | null>) {
      state.activeDocumentId = action.payload;
    },
    setSelectedVersionId(state, action: PayloadAction<string | null>) {
      state.selectedVersionId = action.payload;
    },
  },
});

export const { setActiveDocumentId, setSelectedVersionId } = editorSlice.actions;
export const editorReducer = editorSlice.reducer;
