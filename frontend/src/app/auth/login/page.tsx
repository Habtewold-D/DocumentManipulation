import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <main className="mx-auto grid min-h-screen max-w-6xl items-center gap-6 px-4 py-8 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Welcome back</CardTitle>
          <CardDescription>Continue editing documents and managing draft versions.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-3 text-sm text-muted-foreground">
            <li className="rounded-md border p-3">Run natural language PDF commands</li>
            <li className="rounded-md border p-3">Track every draft and tool execution</li>
            <li className="rounded-md border p-3">Accept only final approved versions</li>
          </ul>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <LoginForm />
        <p className="text-center text-sm text-muted-foreground">
          No account? <Link className="underline" href="/auth/register">Register</Link>
        </p>
      </div>
    </main>
  );
}
