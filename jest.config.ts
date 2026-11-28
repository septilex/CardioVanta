import nextJest from 'next/jest.js'
 
const createJestConfig = nextJest({
  dir: './',
})
 
const config = {
  modulePathIgnorePatterns: ['<rootDir>/.next/'],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testEnvironment: 'jest-environment-jsdom',
}
 
export default createJestConfig(config)
