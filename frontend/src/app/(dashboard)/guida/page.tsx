import { readFile } from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import rehypeAutolinkHeadings from "rehype-autolink-headings";
import GithubSlugger from "github-slugger";

import { Toc, type TocItem } from "./toc";
import "./prose.css";

export const metadata = {
  title: "Guida Utente — N2O DVR",
};

type Frontmatter = {
  title?: string;
  description?: string;
  updated?: string;
};

async function loadGuide() {
  const filePath = path.join(
    process.cwd(),
    "public",
    "guida",
    "GUIDA_UTENTE.md"
  );
  const raw = await readFile(filePath, "utf-8");
  const parsed = matter(raw);
  return {
    content: parsed.content,
    meta: parsed.data as Frontmatter,
  };
}

function extractToc(markdown: string): TocItem[] {
  const slugger = new GithubSlugger();
  const items: TocItem[] = [];
  const lines = markdown.split("\n");
  let inCodeBlock = false;

  for (const line of lines) {
    if (line.startsWith("```")) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) continue;

    const h2 = /^##\s+(.+?)\s*$/.exec(line);
    const h3 = /^###\s+(.+?)\s*$/.exec(line);
    if (h2) {
      const text = h2[1].trim();
      items.push({ id: slugger.slug(text), text, level: 2 });
    } else if (h3) {
      const text = h3[1].trim();
      items.push({ id: slugger.slug(text), text, level: 3 });
    }
  }
  return items;
}

function rewriteImageSrc(src: string | undefined): string | undefined {
  if (!src) return src;
  if (src.startsWith("./images/")) return `/guida/${src.slice(2)}`;
  if (src.startsWith("images/")) return `/guida/${src}`;
  return src;
}

export default async function GuidaPage() {
  const { content, meta } = await loadGuide();
  const toc = extractToc(content);

  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <h1 className="type-h1">{meta.title ?? "Guida Utente"}</h1>
        {meta.description && (
          <p className="type-body max-w-2xl">{meta.description}</p>
        )}
        {meta.updated && (
          <p className="type-caption text-[#64748d]">
            Ultimo aggiornamento: {meta.updated}
          </p>
        )}
      </header>

      <div className="grid gap-10 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="hidden lg:block">
          <div className="sticky top-8">
            <Toc items={toc} />
          </div>
        </aside>

        <article className="min-w-0 max-w-[760px]">
          <div className="guida-prose">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[
                rehypeSlug,
                [
                  rehypeAutolinkHeadings,
                  {
                    behavior: "append",
                    properties: {
                      className: ["heading-anchor"],
                      ariaHidden: true,
                      tabIndex: -1,
                    },
                    content: { type: "text", value: "#" },
                  },
                ],
              ]}
              urlTransform={(url) => rewriteImageSrc(url) ?? ""}
            >
              {content}
            </ReactMarkdown>
          </div>
        </article>
      </div>
    </div>
  );
}
