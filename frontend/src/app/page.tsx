import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-4">
      <div className="space-y-4 text-center">
        <h1 className="text-3xl font-semibold">PDF Agent</h1>
        <p className="text-sm text-muted-foreground">Upload, edit, version, and compare PDFs with AI workflows.</p>
        <div className="flex justify-center gap-3">
          <Link className="rounded border px-4 py-2 text-sm" href="/auth/login">
            Sign in
          </Link>
          <Link className="rounded border px-4 py-2 text-sm" href="/auth/register">
            Register
          </Link>
        </div>
      </div>
    </main>
  );
}
