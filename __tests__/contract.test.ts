import fs from 'fs';
import path from 'path';
import { initialData } from '../src/app/assessment/page';

describe('Frontend Contract Verification', () => {
  let schema: any;

  beforeAll(() => {
    const schemaPath = path.resolve(__dirname, '../configs/feature_schema.json');
    const fileContent = fs.readFileSync(schemaPath, 'utf-8');
    schema = JSON.parse(fileContent);
  });

  it('verifies that feature_schema.json has exactly 13 features', () => {
    expect(schema.feature_count).toBe(13);
    expect(schema.features.length).toBe(13);
  });

  it('verifies that initialData has exactly the 13 fields defined in the schema', () => {
    const initialDataKeys = Object.keys(initialData);
    expect(initialDataKeys.length).toBe(13);

    const schemaFeatureNames = schema.features.map((f: any) => f.name);
    
    // Check all keys in initialData are in schema
    initialDataKeys.forEach((key) => {
      expect(schemaFeatureNames).toContain(key);
    });

    // Check all schema features are in initialData
    schemaFeatureNames.forEach((name: string) => {
      expect(initialDataKeys).toContain(name);
    });
  });

  it('verifies that initialData default values are valid according to the schema', () => {
    schema.features.forEach((feature: any) => {
      const defaultValue = initialData[feature.name as keyof typeof initialData];
      
      if (feature.type === 'binary' || feature.type === 'categorical') {
        expect(feature.allowed_values).toContain(defaultValue);
      } else if (feature.type === 'continuous') {
        expect(typeof defaultValue).toBe('number');
      }
    });
  });
});
