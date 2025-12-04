import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RegisterForm } from "@/components/auth/RegisterForm";

export default function RegisterPage() {
  return (
    <main className="mx-auto grid min-h-screen max-w-6xl items-center gap-6 px-4 py-8 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Create your workspace</CardTitle>
          <CardDescription>Set up your account and start document workflows in minutes.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-3 text-sm text-muted-foreground">
            <li className="rounded-md border p-3">Secure authentication with JWT sessions</li>
            <li className="rounded-md border p-3">Cloud-hosted PDF assets and version history</li>
            <li className="rounded-md border p-3">Tool logs for transparent operations</li>
          </ul>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <RegisterForm />
        <p className="text-center text-sm text-muted-foreground">
          Already have an account? <Link className="underline" href="/auth/login">Sign in</Link>
        </p>
      </div>
    </main>
  );
}
