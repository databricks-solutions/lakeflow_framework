Development Steps
#################

This guide outlines the process for contributing features or fixes to the Lakeflow Framework.

Issue Creation
--------------
1. Create a new issue in the GitHub repository
   
   - Clearly describe the feature or bug
   - Include acceptance criteria
   - Add relevant labels (feature/bug/enhancement)
   - Link to related issues if applicable

Branch Management
-----------------
1. Create a feature branch from develop
   
   - Use naming convention: ``feature/[brief-description]``
   - Example: ``feature/add-scd2-support``
2. Keep branches focused on single features/fixes
3. Regularly sync with develop to avoid merge conflicts

Development Process
-------------------
1. Local Development
   
   - Follow coding standards and style guides
       - Ensure the yapf extention is installed and enabled in VS Code (refer to step 2 of :doc:`contributor_dev_env`)
       - Use yapf to format your python code (right click and select 'Format Document With' then select yapf)
   - Stick to solid principles and object oriented design patterns
   - Deploy updated framework to Databricks to ensure it is working as expected
   - Use meaningful commit messages
   - Keep commits atomic and focused

2. Unit Testing
   
   - Write unit tests per :doc:`contributor_unit_test`
   - Test both success and failure scenarios
   - Ensure test coverage meets requirements
   - Run existing test suite to check for regressions

3. Integration Testing  / Samples
 
   - Where applicable, add sample pipelines to bronze or silver to show how to use the new feature
   - Deploy and run existing sample pipelines on Databricks to ensure changes are not breaking existing functionality (refer to :doc:`deploy_samples`)

4. Documentation
   - Update documentation per :doc:`contributor_dev_docs`

Pull Request Process
--------------------
1. PR Creation
   
   - Create PR from feature branch to develop
   - Fill out PR template completely
   - Link related issues
   - Add relevant reviewers

2. PR Review
   
   - Address reviewer comments
   - Update code/docs as needed
   - Get required approvals

3. Merge Process
   
   - **Squash and merge** to develop
   - Delete feature branch after merge
   - Close related issues

Post-Merge Steps
----------------
1. Verify Changes
   
   - Confirm changes are working in develop
   - Check documentation is published correctly
   - Validate CI/CD pipeline passes

2. Monitor
   
   - Watch for any issues in develop
   - Be prepared to address any problems quickly




