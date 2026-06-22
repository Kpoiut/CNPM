import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const trustSource = await readFile(new URL('./TrustCenter.jsx', import.meta.url), 'utf8')
const methodologySource = await readFile(new URL('./Methodology.jsx', import.meta.url), 'utf8')
const aboutSource = await readFile(new URL('./About.jsx', import.meta.url), 'utf8')
const loginSource = await readFile(new URL('./Login.jsx', import.meta.url), 'utf8')

test('trang Độ tin cậy có nội dung giải thích đầy đủ thay vì chỉ hero', () => {
  assert.match(trustSource, /Cách đọc kết quả/)
  assert.match(trustSource, /Bậc bằng chứng E1–E5/)
  assert.match(trustSource, /Giới hạn cần biết/)
  assert.match(trustSource, /Khoảng dự đoán/)
})

test('trang Phương pháp mô tả pipeline, metric và cơ chế kiểm soát', () => {
  assert.match(methodologySource, /Luồng định giá/)
  assert.match(methodologySource, /MAPE/)
  assert.match(methodologySource, /Conformal prediction/)
  assert.match(methodologySource, /Không tự động promote/)
})

test('hero Giới thiệu dùng ảnh nền toàn chiều ngang có giới hạn chiều cao', () => {
  assert.match(aboutSource, /className="about-hero info-hero"/)
  assert.match(aboutSource, /about-hero__content/)
  assert.doesNotMatch(aboutSource, /gridTemplateColumns: 'minmax\(0, 1\.2fr\)/)
})

test('đăng nhập xong đi vào đúng workspace theo role thay vì quay về trang public', () => {
  assert.match(loginSource, /\/admin\/overview/)
  assert.match(loginSource, /\/app\/valuations\/new/)
  assert.doesNotMatch(loginSource, /navigate\('\/', \{ replace: true \}\)/)
})
