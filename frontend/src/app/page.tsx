import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-10 md:py-16">
      <div className="grid items-stretch gap-6 md:grid-cols-5">
        <Card className="md:col-span-3">
          <CardHeader>
            <p className="text-sm text-muted-foreground">AI-Powered Document Workspace</p>
            <CardTitle className="text-3xl md:text-4xl">PDF Agent</CardTitle>
            <CardDescription className="max-w-xl text-base">
              Upload, edit, version, and compare PDFs using natural-language commands backed by MCP tools.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border bg-muted/30 p-3 text-sm">Natural language editing</div>
              <div className="rounded-md border bg-muted/30 p-3 text-sm">Version accept/reject workflow</div>
              <div className="rounded-md border bg-muted/30 p-3 text-sm">Page-level comparison</div>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href="/auth/login">Sign in</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/auth/register">Create account</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>How it works</CardTitle>
            <CardDescription>Simple flow from upload to approved output.</CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="space-y-3 text-sm text-muted-foreground">
              <li className="rounded-md border p-3">1. Upload a PDF from dashboard</li>
              <li className="rounded-md border p-3">2. Run edit commands in the document workspace</li>
              <li className="rounded-md border p-3">3. Review draft versions and accept or reject</li>
            </ol>
          </CardContent>
        </Card>
      </div>

    </main>
  );
}
