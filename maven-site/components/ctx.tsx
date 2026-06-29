"use client";
import { createContext, useContext } from "react";

export type View = "market" | "chat" | "watchlist" | "themes" | "saved" | "settings";
export type MavenCtxType = {
  subject: string | null;
  setSubject: (s: string | null) => void;
  goChat: (s?: string) => void;
};
export const MavenCtx = createContext<MavenCtxType>({
  subject: null,
  setSubject: () => {},
  goChat: () => {},
});
export const useMaven = () => useContext(MavenCtx);