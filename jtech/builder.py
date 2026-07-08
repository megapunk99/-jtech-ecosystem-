"""
JTECH App Builder — Lovable-style full-stack web application generator.

Inspired by Lovable.dev, Bolt.new, and v0:
- Generates complete React/TypeScript/Tailwind apps (with live previews)
- Standardized Supabase backend (auth, database, storage)
- Visual editing capabilities (component manipulation)
- Live preview HTML generation
- GitHub-ready project structure

The builder creates actual, runnable web applications.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jtech.llm import get_llm, ThinkingEffort, ReasoningTrace

logger = logging.getLogger(__name__)

# ── STANDARDIZED STACK TEMPLATES ────────────────────────────────

STACKS = {
    "react-ts": {
        "name": "React + TypeScript + Tailwind",
        "files": {
            "package.json": """{
  "name": "%(name)s",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@supabase/supabase-js": "^2.45.0",
    "lucide-react": "^0.460.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0"
  }
}""",
            "tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}""",
            "vite.config.ts": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true
  }
})""",
            "postcss.config.js": """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}""",
            "tailwind.config.js": """/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: %(colors)s
    },
  },
  plugins: [],
}""",
            "index.html": """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/logo.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>%(name)s</title>
  </head>
  <body class="bg-gray-50 text-gray-900 antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>""",
            "src/main.tsx": """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)""",
            "src/index.css": """@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
}
""",
            "src/vite-env.d.ts": """/// <reference types="vite/client" />
""",
            "src/App.tsx": """// %(name)s — Built by JTECH
// %(description)s

import React, { useState, useEffect } from 'react'
%(components_import)s

export default function App() {
  return (
    <div className="min-h-screen">
      %(app_content)s
    </div>
  )
}
""",
            "src/lib/supabase.ts": """import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
""",
            ".env.example": """VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
""",
        }
    },
    "python-api": {
        "name": "Python FastAPI + SQLite",
        "files": {
            "requirements.txt": """fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlalchemy>=2.0.0
pydantic>=2.8.0
python-dotenv>=1.0.0
httpx>=0.27.0
""",
            "main.py": """\"\"\"%(name)s — Built by JTECH
%(description)s
\"\"\"

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="%(name)s",
    description="%(description)s",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"service": "%(name)s", "status": "operational"}

@app.get("/health")
async def health():
    return {"status": "ok"}
""",
            ".env.example": """# Configuration
DATABASE_URL=sqlite:///data.db
API_KEY=your_api_key_here
""",
            "run.py": """#!/usr/bin/env python3
\"\"\"Run the %(name)s API server.\"\"\"
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
""",
        }
    },
}

DEFAULT_STACK = "react-ts"

# ── LIVE PREVIEW TEMPLATE ───────────────────────────────────────

LIVE_PREVIEW_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>%(name)s — Preview</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: %(colors)s
        }
      }
    }
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    * { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
    body { margin: 0; padding: 0; }
    .preview-badge {
      position: fixed; top: 12px; right: 12px;
      background: rgba(0,0,0,0.7); color: white;
      padding: 6px 14px; border-radius: 20px;
      font-size: 12px; font-weight: 500;
      backdrop-filter: blur(8px);
      z-index: 9999;
      pointer-events: none;
    }
  </style>
</head>
<body>
  <div class="preview-badge">JTECH ⚡ Live Preview</div>
  %(app_html)s
</body>
</html>"""


class AppBuilder:
    """
    Lovable-style full-stack web application builder.

    Generates complete, runnable web applications with:
    - React/TypeScript/Tailwind frontend
    - Supabase backend integration
    - Live preview HTML
    - Visual component manipulation
    - Production-ready project structure

    Usage:
        builder = AppBuilder()
        result = builder.build_app("A task management dashboard")
        # result contains: files, preview_html, structure, metadata
    """

    def __init__(self):
        self.llm = get_llm()
        self.work_dir = Path(os.environ.get("JTECH_PROJECTS_DIR", "./built_products"))
        self.work_dir.mkdir(parents=True, exist_ok=True)

    # ── PUBLIC API ──────────────────────────────────────────────

    def build_app(self, product_idea: dict, stack: str = DEFAULT_STACK) -> dict:
        """
        Build a complete web application from a product idea.

        Pipeline:
        1. Analyze requirements (DeepSeek thinking)
        2. Design component tree
        3. Generate all source files
        4. Generate live preview HTML
        5. Create project structure

        Returns dict with:
          - files: {file_path: content}
          - preview_html: standalone preview page
          - structure: project file tree
          - components: list of UI components
          - metadata: app metadata
        """
        name = product_idea.get("product_name", "App")
        description = product_idea.get("description", "")
        features = product_idea.get("features", [])
        data_model = product_idea.get("data_model", [])

        slug = name.lower().replace(" ", "-").replace("_", "-")
        project_path = self.work_dir / slug
        project_path.mkdir(parents=True, exist_ok=True)

        # Step 1: Deep analysis — think before building
        logger.info("   🔍 Analyzing requirements...")
        analysis = self._analyze_requirements(name, description, features)

        # Step 2: Design component tree
        logger.info("   🧩 Designing component architecture...")
        components = self._design_components(name, description, features, analysis)

        # Step 3: Generate app logic (the main App.tsx or equivalent)
        logger.info("   ⚡ Generating application logic...")
        app_logic = self._generate_app_logic(name, description, features, components, analysis)

        # Step 4: Generate all files
        logger.info("   📁 Generating project files...")
        files = self._generate_project_files(name, description, stack, components, app_logic, analysis)

        # Step 5: Generate live preview
        logger.info("   🖥️  Building live preview...")
        preview_html = self._generate_preview(name, description, components, app_logic, analysis)

        # Step 6: Write files to disk
        logger.info("   💾 Writing files...")
        written_paths = self._write_files(files, project_path)

        # Return complete build result
        return {
            "name": name,
            "description": description,
            "slug": slug,
            "project_path": str(project_path),
            "files": files,
            "written_files": written_paths,
            "preview_html": preview_html,
            "components": components,
            "stack": STACKS.get(stack, STACKS[DEFAULT_STACK])["name"],
            "analysis": analysis,
            "metadata": {
                "built_at": datetime.now().isoformat(),
                "stack": stack,
                "component_count": len(components),
                "file_count": len(files),
            },
        }

    def generate_preview(self, product_data: dict, component_data: Optional[dict] = None) -> str:
        """Generate a standalone live preview HTML page — like Lovable's preview pane."""
        name = product_data.get("name", "Product")
        desc = product_data.get("description", "")
        components = component_data or product_data.get("components", [])
        scheme = self._get_color_scheme(name, components)

        # Build component HTML
        component_html = self._render_components_preview(components)

        return LIVE_PREVIEW_TEMPLATE % {
            "name": name,
            "colors": json.dumps(scheme),
            "app_html": component_html,
        }

    def suggest_visual_edits(self, current_html: str, instruction: str) -> str:
        """
        Visual editing mode — like Lovable's click-to-edit.
        Takes current HTML and an edit instruction, returns modified HTML.
        """
        prompt = (
            f"You are a visual UI editor. Modify the following HTML according to the instruction.\n\n"
            f"INSTRUCTION: {instruction}\n\n"
            f"CURRENT HTML:\n```html\n{current_html[:3000]}\n```\n\n"
            f"Rules:\n"
            f"- ONLY output the modified HTML, no explanations\n"
            f"- Preserve the overall structure and functionality\n"
            f"- Use Tailwind CSS classes for styling\n"
            f"- Keep the design consistent with existing style\n"
            f"- Make the HTML self-contained (includes Tailwind CDN)\n"
        )

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You modify HTML precisely. Output ONLY the modified HTML code.",
            thinking_effort=ThinkingEffort.HIGH,
            max_tokens=8192,
        ) or current_html

    # ── REQUIREMENT ANALYSIS (DeepSeek thinking) ────────────────

    def _analyze_requirements(self, name: str, description: str, features: list[str]) -> dict:
        """Deep analysis of what needs to be built — with thinking mode."""
        prompt = (
            f"Analyze this product and design its technical requirements:\n\n"
            f"Product: {name}\n"
            f"Description: {description}\n"
            f"Features: {json.dumps(features)}\n\n"
            f"Think step-by-step about:\n"
            f"1. What pages/views are needed?\n"
            f"2. What data does each page need?\n"
            f"3. What user interactions happen?\n"
            f"4. What's the data flow?\n"
            f"5. What external APIs are needed?\n"
            f"6. What's the authentication model?\n\n"
            f"Output JSON:\n"
            f"{{\n"
            f'  "pages": [{{"name": "Dashboard", "path": "/", "purpose": "..."}}],\n'
            f'  "data_requirements": [{{"entity": "User", "fields": [...]}}],\n'
            f'  "user_flows": ["Sign up → Create → Share"],\n'
            f'  "api_endpoints": [{{"method": "GET", "path": "/api/items"}}],\n'
            f'  "auth_model": "supabase/anonymous/api_key",\n'
            f'  "key_features": ["Feature 1", "Feature 2"]\n'
            f"}}"
        )

        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": prompt}],
            system_prompt="You are a senior solutions architect. Think deeply before designing.",
            thinking_effort=ThinkingEffort.DEEP,
        )

        if result:
            # Log the reasoning for transparency
            if reasoning.steps:
                logger.debug(f"   🤔 Analysis reasoning: {len(reasoning.steps)} steps, "
                             f"{len(reasoning.self_corrections)} self-corrections")
            return result

        return {
            "pages": [{"name": "Dashboard", "path": "/", "purpose": "Main interface"}],
            "key_features": features or ["Core functionality"],
        }

    # ── COMPONENT DESIGN ────────────────────────────────────────

    def _design_components(self, name: str, description: str,
                           features: list[str], analysis: dict) -> list[dict]:
        """Design the React component tree — like Lovable's component architecture."""
        prompt = (
            f"Design the React component tree for this application:\n\n"
            f"Product: {name}\n"
            f"Description: {description}\n"
            f"Features: {json.dumps(features)}\n"
            f"Pages: {json.dumps(analysis.get('pages', []))}\n\n"
            f"For each component, provide:\n"
            f"{{\n"
            f'  "name": "ComponentName",\n'
            f'  "type": "page/layout/widget/input/display",\n'
            f'  "description": "What it does",\n'
            f'  "props": ["prop1: string", "prop2: number"],\n'
            f'  "children": ["ChildComponent1", "ChildComponent2"],\n'
            f'  "state": ["stateVar: type"],\n'
            f'  "styling": "Tailwind classes for container",\n'
            f'  "interactions": ["onClick: does X", "onSubmit: does Y"]\n'
            f"}}\n\n"
            f"Output a JSON object with a 'components' array containing 5-12 components.\n"
            f"Cover: layout, navigation, main feature components, and utility components."
        )

        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": prompt}],
            system_prompt="You design React component trees like a senior frontend architect.",
            thinking_effort=ThinkingEffort.HIGH,
        )

        components = result.get("components", []) if result else []
        if not components:
            components = [
                {"name": "Header", "type": "layout", "description": "Top navigation bar"},
                {"name": "MainContent", "type": "layout", "description": "Main content area"},
            ]

        return components

    # ── APP LOGIC GENERATION ────────────────────────────────────

    def _generate_app_logic(self, name: str, description: str,
                            features: list[str], components: list[dict],
                            analysis: dict) -> str:
        """Generate the core application logic code — the main App component."""
        pages = analysis.get("pages", [{"name": "Main", "path": "/"}])
        comp_names = [c["name"] for c in components[:8]]

        prompt = (
            f"Generate the MAIN App component code for this React application:\n\n"
            f"App: {name}\n"
            f"Description: {description}\n"
            f"Pages: {json.dumps(pages)}\n"
            f"Components available: {json.dumps(comp_names)}\n"
            f"Features: {json.dumps(features)}\n\n"
            f"Generate a single, self-contained React functional component.\n"
            f"Requirements:\n"
            f"- Use React (useState, useEffect hooks)\n"
            f"- Use Tailwind CSS for ALL styling\n"
            f"- Use lucide-react for icons (import { Menu, X, ... } from 'lucide-react')\n"
            f"- Include all page/section rendering within this file\n"
            f"- Include sample data rendering (mock data inline)\n"
            f"- Handle loading, empty, and error states\n"
            f"- Responsive design (mobile-first)\n"
            f"- Smooth transitions and hover effects\n"
            f"- Professional, modern UI\n\n"
            f"Output ONLY the TypeScript code for the component. No explanations.\n"
            f"Wrap in ```tsx code blocks."
        )

        code = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You write production-quality React TypeScript code with Tailwind CSS.",
            thinking_effort=ThinkingEffort.HIGH,
            max_tokens=8192,
        ) or ""

        # Extract code from markdown
        code_match = re.search(r'```(?:tsx|ts|jsx|js)?\n(.*?)```', code, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()

        return code

    # ── PROJECT FILE GENERATION ─────────────────────────────────

    def _generate_project_files(self, name: str, description: str,
                                 stack: str, components: list[dict],
                                 app_logic: str, analysis: dict) -> dict[str, str]:
        """Generate all files for a complete project."""
        stack_config = STACKS.get(stack, STACKS[DEFAULT_STACK])
        files = {}

        slug = name.lower().replace(" ", "-").replace("_", "-")
        scheme = self._get_color_scheme(name, components)

        # Generate component files for React stack
        if stack == "react-ts":
            for template_path, template_content in stack_config["files"].items():
                if template_path == "src/App.tsx":
                    # Use generated app logic
                    content = app_logic
                    if not content:
                        content = template_content % {
                            "name": name,
                            "description": description,
                            "components_import": "",
                            "app_content": "<div className='p-8'><h1 className='text-3xl font-bold'>{name}</h1><p className='mt-2 text-gray-600'>{description}</p></div>",
                        }
                    files[template_path] = content
                else:
                    files[template_path] = template_content % {
                        "name": slug,
                        "description": description[:100],
                        "colors": json.dumps(scheme),
                    }

            # Generate component files
            for comp in components[:10]:
                comp_name = comp["name"]
                comp_code = self._generate_component_code(comp, components)
                files[f"src/components/{comp_name}.tsx"] = comp_code

        elif stack == "python-api":
            for template_path, template_content in stack_config["files"].items():
                files[template_path] = template_content % {
                    "name": name,
                    "description": description[:200],
                }

        return files

    def _generate_component_code(self, component: dict, all_components: list[dict]) -> str:
        """Generate a single React component file."""
        prompt = (
            f"Generate a React TypeScript component:\n\n"
            f"Component: {component.get('name')}\n"
            f"Type: {component.get('type')}\n"
            f"Description: {component.get('description')}\n"
            f"Props: {component.get('props', [])}\n"
            f"Children: {component.get('children', [])}\n"
            f"State: {component.get('state', [])}\n"
            f"Base styling: {component.get('styling', 'flex items-center')}\n"
            f"Interactions: {component.get('interactions', [])}\n\n"
            f"Requirements:\n"
            f"- TypeScript with proper types\n"
            f"- Tailwind CSS for styling\n"
            f"- lucide-react for icons\n"
            f"- Handle loading/empty/error states if applicable\n"
            f"- Responsive design\n"
            f"- Export as default\n\n"
            f"Output ONLY the code in ```tsx blocks."
        )

        code = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You write clean, production-ready React components.",
            max_tokens=4096,
        ) or ""

        code_match = re.search(r'```(?:tsx|ts|jsx)?\n(.*?)```', code, re.DOTALL)
        return (code_match.group(1).strip() if code_match else code) or (
            f"// {component['name']} component\n"
            f"import React from 'react'\n\n"
            f"export default function {component['name']}() {{\n"
            f"  return <div className='p-4'>{component['name']} component</div>\n"
            f"}}"
        )

    # ── LIVE PREVIEW GENERATION ─────────────────────────────────

    def _generate_preview(self, name: str, description: str,
                          components: list[dict], app_logic: str,
                          analysis: dict) -> str:
        """Generate a standalone live preview HTML page."""
        scheme = self._get_color_scheme(name, components)

        prompt = (
            f"Generate a STUNNING, complete HTML preview page for this app:\n\n"
            f"App: {name}\n"
            f"Description: {description}\n"
            f"Features: {json.dumps(analysis.get('key_features', []))}\n"
            f"Pages: {json.dumps(analysis.get('pages', []))}\n\n"
            f"Create a FULL, production-quality landing page with:\n"
            f"- Hero section with animated gradient/text\n"
            f"- Features grid with cards\n"
            f"- Pricing or CTA section\n"
            f"- Modern, premium design\n"
            f"- Tailwind CSS (via CDN)\n"
            f"- Smooth scroll and transitions\n"
            f"- Responsive layout\n"
            f"- Color scheme: {json.dumps(scheme)}\n"
            f"- Font: Inter from Google Fonts\n\n"
            f"Output the ENTIRE HTML document. Make it beautiful."
        )

        html = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You build stunning, production-quality HTML pages. Think Stripe/Linear quality.",
            thinking_effort=ThinkingEffort.DEEP,
            max_tokens=8192,
            temperature=0.4,
        ) or ""

        if "<html" not in html and "<!DOCTYPE" not in html:
            html = LIVE_PREVIEW_TEMPLATE % {
                "name": name,
                "colors": json.dumps(scheme),
                "app_html": html,
            }

        return html

    def _render_components_preview(self, components: list[dict]) -> str:
        """Render components into preview HTML."""
        cards = ""
        for comp in components[:8]:
            name = comp.get("name", "Component")
            desc = comp.get("description", "")
            cards += f"""
            <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
              <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm mb-3">
                {name[0]}
              </div>
              <h3 class="font-semibold text-gray-900">{name}</h3>
              <p class="text-sm text-gray-500 mt-1">{desc}</p>
            </div>"""
        return f"""
        <div class="min-h-screen bg-gray-50">
          <header class="bg-white border-b border-gray-100 px-6 py-4">
            <div class="max-w-6xl mx-auto flex items-center justify-between">
              <h1 class="text-xl font-bold text-gray-900">App Preview</h1>
              <span class="text-sm text-gray-400">Built by JTECH</span>
            </div>
          </header>
          <main class="max-w-6xl mx-auto p-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {cards}
            </div>
          </main>
        </div>"""

    # ── COLOR SCHEME ────────────────────────────────────────────

    def _get_color_scheme(self, name: str, components: list[dict]) -> dict:
        """Generate a cohesive color scheme for the app."""
        prompt = (
            f"Generate a beautiful 4-color Tailwind color scheme for this app:\n\n"
            f"App: {name}\n"
            f"Components: {json.dumps([c['name'] for c in components[:5]])}\n\n"
            f"Output JSON: {{\"primary\": \"#hex\", \"secondary\": \"#hex\", "
            f"\"accent\": \"#hex\", \"background\": \"#hex\"}}\n"
            f"Make it modern and cohesive. Think Linear, Notion, Stripe quality."
        )

        result = self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system_prompt="You create beautiful color palettes.",
            thinking_effort=ThinkingEffort.MINIMAL,
        )
        return result or {
            "primary": "#3b82f6",
            "secondary": "#8b5cf6",
            "accent": "#06b6d4",
            "background": "#f8fafc",
        }

    # ── FILE WRITING ────────────────────────────────────────────

    def _write_files(self, files: dict[str, str], project_path: Path) -> list[str]:
        """Write generated files to disk."""
        written = []
        for file_path, content in files.items():
            full_path = project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                written.append(str(full_path))
            except Exception as e:
                logger.error(f"Failed to write {full_path}: {e}")
        return written
