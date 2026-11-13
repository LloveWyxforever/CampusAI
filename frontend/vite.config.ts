import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({base:process.env.CAMPUSAI_PAGES==='1'?'/CampusAI/':'/',define:{__PAGES_DEMO__:JSON.stringify(process.env.CAMPUSAI_PAGES==='1')},plugins:[react(),tailwindcss()],server:{proxy:{'/api':'http://127.0.0.1:8000'}}})
