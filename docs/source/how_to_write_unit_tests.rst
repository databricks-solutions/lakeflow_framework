How to Create Unit Test Functions for a Project Using `pytest` and `unittest`
==========================================================================

Prerequisites
-------------
1. **Install `pytest` and `unittest` (if not already installed):**

   - Install `pytest`:
     ```bash
     pip install pytest
     ```
   - `unittest` is included in Python’s standard library, so no additional installation is required.

2. **Project Setup:**

   Organise your project files in a logical structure:
::

    my_project/
    ├── src/
    │   ├── module.py       # Your source code
    ├── tests/
    │   ├── test_module.py  # Your test files
    ├── requirements.txt
    └── README.md

Writing Unit Test Functions with `pytest`
-----------------------------------------

1. **Test File Naming:**
   
   Name test files starting with `test_` or ending with `_test.py`, e.g., `test_module.py`.

2. **Test Function Naming:**
   
   Name test functions starting with `test_`, e.g., `test_add_function`.

3. **Basic Structure:**
   
   .. code-block:: python

      import pytest
      from src.module import add

      def test_add_function():
          # Arrange
          a, b = 2, 3

          # Act
          result = add(a, b)

          # Assert
          assert result == 5

4. **Using Fixtures:**
   
   Use `@pytest.fixture` to set up reusable test data or objects.

   .. code-block:: python

      @pytest.fixture
      def sample_data():
          return {"a": 2, "b": 3}

      def test_add_function_with_fixture(sample_data):
          result = add(sample_data["a"], sample_data["b"])
          assert result == 5

5. **Running Tests:**

   - Run all tests:
     ```bash
     pytest
     ```
   - Run a specific test file:
     ```bash
     pytest tests/test_module.py
     ```

Writing Unit Test Functions with `unittest`
-------------------------------------------

1. **Test File Naming:**

   The naming convention is not strict, but `test_*.py` is commonly used.

2. **Basic Structure:**

   Inherit from `unittest.TestCase` to define test cases.

   .. code-block:: python

      import unittest
      from src.module import add

      class TestAddFunction(unittest.TestCase):
          def test_add(self):
              # Arrange
              a, b = 2, 3

              # Act
              result = add(a, b)

              # Assert
              self.assertEqual(result, 5)

      if __name__ == "__main__":
          unittest.main()

3. **Using `setUp` and `tearDown`:**

   Define `setUp` and `tearDown` methods for reusable setup and cleanup logic.

   .. code-block:: python

      class TestAddFunction(unittest.TestCase):
          def setUp(self):
              self.a = 2
              self.b = 3

          def tearDown(self):
              # Clean up resources, if any
              pass

          def test_add(self):
              result = add(self.a, self.b)
              self.assertEqual(result, 5)

4. **Running Tests:**

   - Run all tests in a file:
     ```bash
     python -m unittest discover
     ```
   - Run a specific test file:
     ```bash
     python -m unittest tests/test_module.py
     ```

General Tips for Writing Unit Tests
-----------------------------------

1. **Follow the AAA Pattern:**

   - **Arrange:** Set up test data and preconditions.
   - **Act:** Execute the function or method under test.
   - **Assert:** Verify the result matches expectations.

2. **Use Mocks and Stubs:**

   Use `unittest.mock` or `pytest-mock` to replace external dependencies or isolate units.

3. **Group Related Tests:**

   Use classes or organise tests logically to improve readability.

4. **Test Edge Cases:**

   Test normal, boundary, and error conditions.

Example: Pytest vs. Unittest
----------------------------

**Using `pytest`:**

.. code-block:: python

   import pytest
   from src.module import divide

   def test_divide_by_nonzero():
       assert divide(10, 2) == 5

   def test_divide_by_zero():
       with pytest.raises(ZeroDivisionError):
           divide(10, 0)

**Using `unittest`:**

.. code-block:: python

   import unittest
   from src.module import divide

   class TestDivideFunction(unittest.TestCase):
       def test_divide_by_nonzero(self):
           self.assertEqual(divide(10, 2), 5)

       def test_divide_by_zero(self):
           with self.assertRaises(ZeroDivisionError):
               divide(10, 0)

Both frameworks achieve the same goals but differ in syntax and flexibility. Choose based on project requirements and personal preference.

