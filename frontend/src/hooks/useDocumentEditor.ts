"use client";

import { useAppDispatch, useAppSelector } from "@/hooks/useRedux";
import { setActiveDocumentId, setSelectedVersionId } from "@/state/editor-store";

export function useDocumentEditor() {
  const dispatch = useAppDispatch();
  const editor = useAppSelector((state) => state.editor);

  return {
    editor,
    setActiveDocument: (documentId: string | null) => dispatch(setActiveDocumentId(documentId)),
    setSelectedVersion: (versionId: string | null) => dispatch(setSelectedVersionId(versionId)),
  };
}
