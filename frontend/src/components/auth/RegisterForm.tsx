"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { User, Mail, Lock } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function RegisterForm() {
  const router = useRouter();
  const { register, loading, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const ok = await register(email, password, fullName);
    if (ok) {
      router.push("/auth/login");
    }
  };

  return (
    <Card className="w-full max-w-md overflow-hidden shadow-lg border-primary/15 animate-fade-in">
      <div className="h-1.5 gradient-primary" />
      <CardHeader className="pb-4">
        <CardTitle className="text-2xl">Create account</CardTitle>
        <CardDescription>Start your PDF workspace with versioned editing and review tools.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="relative">
            <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Full name (optional)"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="pl-10"
              required
            />
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="pl-10"
              required
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" className="w-full gradient-primary border-0 text-white shadow-sm hover:shadow-md transition-shadow" disabled={loading}>
            {loading ? "Creating account..." : "Register"}
          </Button>
          <p className="text-center text-xs text-muted-foreground">Already have access? Sign in after registration.</p>
        </form>
      </CardContent>
    </Card>
  );
}
