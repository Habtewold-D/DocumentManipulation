"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FileText, LogOut, UserPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { clearAccessToken, getAccessToken, subscribeAuthToken } from "@/lib/auth/token-storage";

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const isAuthenticated = useSyncExternalStore(
    subscribeAuthToken,
    () => Boolean(getAccessToken()),
    () => false,
  );

  const hideHeader = pathname?.startsWith("/auth/");
  if (hideHeader) return null;

  const onSignOut = () => {
    clearAccessToken();
    router.push("/auth/login");
    router.refresh();
  };

  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-lg">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link
          href={isAuthenticated ? "/dashboard" : "/"}
          className="flex items-center gap-2 font-semibold tracking-tight transition-colors hover:text-primary"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg gradient-primary text-white shadow-sm">
            <FileText className="h-4 w-4" />
          </span>
          <span className="text-lg">PDF Agent</span>
        </Link>
        <nav className="flex items-center gap-1.5">
          {isAuthenticated ? (
            <>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={onSignOut}>
                <LogOut className="h-4 w-4" />
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm" className="gap-1.5 text-muted-foreground hover:text-foreground">
                <Link href="/auth/login">Sign in</Link>
              </Button>
              <Button asChild size="sm" className="gap-1.5 gradient-primary border-0 text-white shadow-sm hover:shadow-md transition-shadow">
                <Link href="/auth/register">
                  <UserPlus className="h-4 w-4" />
                  Register
                </Link>
              </Button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
